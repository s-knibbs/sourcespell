# SourceSpell - Command line spell checker for source code files.
#
# Copyright 2016 - Simon J Knibbs <simon.knibbs@gmail.com>

from __future__ import print_function

import os
import codecs
import sys
import argparse
import bisect
import re
import fnmatch
import pkg_resources
from collections import OrderedDict

import enchant
from enchant.tokenize import get_tokenizer, URLFilter, WikiWordFilter, Filter
import pygments
from pygments import lexers
from pygments.filters import TokenMergeFilter
from pygments.token import Comment, String, Token, Generic, Literal
from colorama import Fore, Back, Style, init

try:
    import magic
except ImportError:
    magic = None

if sys.platform == "win32":
    import msvcrt
    getchar = msvcrt.getch
else:  # POSIX platforms
    import tty
    import termios

    def getchar():
        """Gets a character from stdin without waiting
        for a newline.

        :returns: A single character from stdin.
        """
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch


NAME = 'SourceSpell'
DESCRIPTION = "%s - Command line spellchecker for source code files." % NAME


class EmptyFileError(Exception):
    """Error thrown for empty files."""
    pass


class ParseError(Exception):
    """Error thrown for Pygments lexer errors."""
    pass


class NextFile(Exception):
    """Trigger to advance to the next file."""
    pass


class HashBangFilter(Filter):
    """Filter skipping over the hashbang in executable scripts.

    Taken from: https://github.com/htgoebel/pysource-spellchecker
    """
    _pattern = re.compile(r"^#!/.+$")

    def _skip(self, word):
        if self._pattern.match(word):
            return True
        return False


class MyWikiWordFilter(WikiWordFilter):

    def _skip(self, text):
        print(text)
        WikiWordFilter._skip(self, text)


class EmailFilter(enchant.tokenize.EmailFilter):
    """Override the :class:`enchant.tokenize.EmailFilter` to filter out
    addresses enclosed in angle brackets, for example:

        <joe.bloggs@example.com>
    """
    _pattern = re.compile(r"^.+@[^\.].*\.[a-z]{2,}\W?$")


class SpellingCorrection(object):
    """Object to store information for a spelling
    error.

    :param filename: File path, relative to the base directory.
    :param word: The word being checked.
    :param index: The file index at the start of the word.
    :param line_no: The 1-indexed line number.
    :param column: The column index.
    :param dictionary: Reference to the dictionary object.
    :type dictionary: :class:`enchant.Dict`
    :param line_content: The contents of the line containing the error.
    """

    def __init__(self, filename, word, index, line_no, column, dictionary, line_content):
        self.filename = filename
        self.word = word
        self.index = index
        self.line_no = line_no
        self.column = column
        self.dictionary = dictionary
        self.line_content = line_content.rstrip()

    def __str__(self):
        """Return a string representation of the error, including
        the filename, line and column numbers.
        """
        return (
            "%s - Ln %s Col %s: %s" %
            (self.filename, self.line_no, self.column, self.word)
        )

    @property
    def suggestions(self):
        """The :class:`list` of suggested corrections."""
        return self.dictionary.suggest(self.word)

    def prompt(self):
        """Generate a prompt listing the available corrections.
        """
        before = self.line_content[:self.column - 1]
        after = self.line_content[self.column - 1 + len(self.word):]
        suggestions = ' | '.join(
            ['%s: %s' % (idx, suggest) for idx, suggest in enumerate(self.suggestions[:10])]
        )
        return '%s%s%s%s%s\n\n%s' % (
            before, Back.RED, self.word,
            Style.RESET_ALL, after, suggestions
        )


def merge_tokens(stream):
    """Merge tokens of the same type from Pygments.

    Adapted from :class:`pygments.filters.TokenMergeFilter`
    """
    (curr_type, curr_value, curr_index) = (None, None, None)
    for index, ttype, value in stream:
        if ttype is curr_type:
            curr_value += value
        else:
            if curr_type is not None:
                yield (curr_index, curr_type, curr_value)
            (curr_type, curr_value, curr_index) = (ttype, value, index)
    if curr_type is not None:
        yield (curr_index, curr_type, curr_value)


class SourceFile(object):
    """Interface for checking for spelling errors in a
    single source file.

    :param filename: Absolute path to the file.
    :param dictionary: Enchant dictionary.
    :type dictionary: :class:`enchant.Dict`
    :param tokeniser: Enchant tokeniser from :func:`get_tokenizer`
    :type tokeniser: :class:`enchant.tokenize.Tokenizer`
    :param base_dir: Base directory path.
    :param encoding: Character set encoding to read files with.
    """

    _rawstring_re = re.compile(r'^r["\']')

    def __init__(self, filename, dictionary, tokeniser, base_dir, encoding='utf-8'):
        self.base_dir = base_dir
        self.filename = filename
        self.dict = dictionary
        # List of indexes of line endings for generating line numbers.
        self.line_idxs = []
        try:
            with codecs.open(self.filename, 'r', encoding) as src_file:
                self.content = src_file.read()
                line_lengths = [len(line) for line in self.content.splitlines(True)]
                if len(line_lengths) > 0:
                    count = 0
                    for length in line_lengths:
                        self.line_idxs.append(length + count)
                        count += length
                else:
                    raise EmptyFileError("%s: File empty." % self.relname)
        except UnicodeDecodeError:
            print(
                "%s: Couldn't decode with '%s' codec." % (self.relname, encoding),
                file=sys.stderr
            )
            raise

        self.code_lexer = self._get_lexer()

        self.tokeniser = tokeniser

    def _get_lexer(self):
        """Initialise the Pygments lexer.
        """
        # TODO: Improve the lexer selection since Jinja and other template languages are
        # often saved with .html template.
        lexer = None
        try:
            lexer = lexers.get_lexer_for_filename(self.filename)
        except pygments.util.ClassNotFound:
            pass

        if magic is not None and lexer is None:
            # Fallback to mimetype detection
            try:
                mimetype = magic.from_file(self.filename, mime=True)
                lexer = lexers.get_lexer_for_mimetype(mimetype)
            except pygments.util.ClassNotFound:
                pass

        if lexer is None:
            try:
                # If all else fails use the guess_lexer method
                lexer = lexers.guess_lexer(self.content[:512])
            except pygments.util.ClassNotFound:
                print("No lexer found for: %s" % self.relname, file=sys.stderr)
                raise

        return lexer

    @property
    def relname(self):
        """Returns the name of the file relative to
        the base directory being checked.
        """
        return self.filename[len(self.base_dir) + 1:]

    def _index_to_col_lineno(self, index):
        """Calculates the line and column index from the
        file index.

        :param index: The file index.
        :returns: A tuple of line number and column index.
        :rtype: :class:`tuple` of (int, int)
        """
        line = bisect.bisect_right(self.line_idxs, index)
        column = index if line == 0 else index - self.line_idxs[line - 1]
        # Note: line and column numbers are 1-indexed
        return (line + 1, column + 1)

    def _filter_code_tokens(self, stream):
        """Filter the token stream based on token type and
        the name of the lexer.
        """
        for index, tokentype, value in merge_tokens(stream):
            # Handle token errors
            if tokentype is Token.Error:
                (line, _) = self._index_to_col_lineno(index)
                raise ParseError('%s: Parse error at line %s.' % (self.relname, line))
            # Lex python doc strings with the reStructuredText lexer.
            if tokentype is String.Doc and self.code_lexer.name == 'Python':
                sub_lexer = lexers.get_lexer_by_name('reStructuredText')
                sub_stream = merge_tokens(sub_lexer.get_tokens_unprocessed(value))
                for sub_index, tktype, value in sub_stream:
                    if self._select_token(tokentype, sub_lexer.name, value):
                        yield (index + sub_index, value)
            else:
                if self._select_token(tokentype, self.code_lexer.name, value):
                    yield (index, value)

    def _select_token(self, tokentype, name, value):
        """Return ``True`` if the token should be used, ``False`` otherwise."""
        # TODO: Make min length configurable.
        MIN_LENGTH = 10

        return (
            (tokentype in Comment and tokentype not in Comment.Preproc) or
            (tokentype in Token.Text) or
            (tokentype in Generic.Emph) or
            (tokentype in Generic.Strong) or
            # Ignore string literals in reStructuredText since
            # these are used class and function references.
            (tokentype in Literal.String and
             len(value) > MIN_LENGTH and
             name != 'reStructuredText' and not
             self._is_rawstring(value))  # Ignore Python raw-string literals
        )

    def _is_rawstring(self, value):
        """Return ``True`` if value is a Python raw-string literal,
        ``False`` otherwise.
        """
        return self._rawstring_re.match(value) is not None

    def errors(self):
        """Generator that yields :class:`SpellingCorrection` objects for the current
        source file.
        """
        stream = self.code_lexer.get_tokens_unprocessed(self.content)
        for index, value in self._filter_code_tokens(stream):
            for word, token_index in self.tokeniser(value):
                if not self.dict.check(word):
                    line, column = self._index_to_col_lineno(index + token_index)
                    # Get line content
                    lo = 0 if line == 1 else self.line_idxs[line - 2]
                    line_content = self.content[lo:self.line_idxs[line - 1]]
                    yield SpellingCorrection(
                        self.relname, word, index + token_index,
                        line, column, self.dict, line_content
                    )


class BaseChecker(object):
    """Common functionality for all checker classes.

    :param base_dir: The path to the base directory.
    :param ignore_patterns: List of glob ignore patterns to skip.
    :param language: ISO language code, e.g. 'en_GB' or 'en_US'
    :param project_dict: Path to the project dictionary for excluded words.
    :param encoding: Character set encoding to use reading / writing files.
    """

    def __init__(self, base_dir='.', ignore_patterns=None, language='en_GB',
                 project_dict=None, encoding='utf-8'):
        self.base_dir = os.path.realpath(base_dir)
        # Ignore common binary file formats and hidden files
        self.ignore_patterns = [
            '*.gif', '*.jpeg', '*.jpg', '*.bmp', '*.png',
            '*.exe', '*.dll', '*.webp', '*.pyc', '*.zip',
            '*.gz', '*/.*'
        ]
        if not os.path.isabs(project_dict):
            project_dict = os.path.abspath(os.path.join(base_dir, project_dict))

        if ignore_patterns is not None:
            self.ignore_patterns.extend(
                [os.path.join(self.base_dir, pattern) for pattern in ignore_patterns]
            )
        self.dictionary = enchant.DictWithPWL(language, project_dict)
        self.ret_code = 0
        self.encoding = encoding

        # TODO: Consider breaking apart WikiWords instead of filtering them out.
        self.tokeniser = get_tokenizer(
            self.dictionary.tag, [EmailFilter, URLFilter, WikiWordFilter, HashBangFilter]
        )

    def _search_files(self):
        """Generator function which returns files to be checked."""
        for root, dirs, files in os.walk(self.base_dir):
            for name in files:
                filename = os.path.join(root, name)
                if any([fnmatch.fnmatch(filename, i) for i in self.ignore_patterns]):
                    continue
                yield filename

    def _process_file(self, src_file):
        """Called from run for each source file
        under the base directory.

        :param src_file: The source file being checked.
        :type src_file: :class:`SourceFile`
        """
        raise NotImplementedError

    def run(self):
        """Runs the checker.

        :returns: The script exit code.
        :rtype: int
        """
        for name in self._search_files():
            try:
                self._process_file(
                    SourceFile(name, self.dictionary, self.tokeniser, self.base_dir, self.encoding)
                )
            except pygments.util.ClassNotFound:
                self.ret_code = 1
                continue
            except ParseError as e:
                print(e, file=sys.stderr)
                self.ret_code = 1
                continue
            except UnicodeDecodeError:
                self.ret_code = 1
                continue
            except (EmptyFileError, NextFile):
                continue  # Skip empty files
            except StopIteration:  # User quit.
                break
        return self.ret_code


class SpellChecker(BaseChecker):
    """Non-Interactive spell checker. Prints a list of
    all spelling errors found.
    """

    def _process_file(self, src_file):
        """Prints errors to stderr and sets the error flag."""
        for error in src_file.errors():
            self.ret_code = 1
            print(error, file=sys.stderr)


class InteractiveChecker(BaseChecker):
    """Interactive spellchecker. Allows the user
    to quickly fix spelling errors and add words to
    the excluded words dictionary.
    """

    def _print_options(self):
        """Prints the list of keyboard options."""
        codes = OrderedDict([
            ('0-9', 'Use the numbered suggestion.'),
            ('a', 'Ignore the error and add to the excluded words.'),
            ('n', 'Go to the next file, save existing changes.'),
            ('q', 'Exit immediately, discards changes in the current file.')
        ])
        print()
        for code, help in codes.items():
            print("%s - %s" % (code, help))
        print("To skip to the next error, press any other key.")

    def _handle_response(self, src_map, error):
        """Handle the user response. Return True
        if a correction was made.

        :param src_map: The map of indexes to tokens.
        :type src_map: :class:`collections.OrderedDict`
        :param error: The spelling correction data.
        :type error: :class:`SpellingCorrection`
        """
        correction = False
        print("--->", end=" ")
        response = getchar()
        # Echo response
        print(response)
        # Correct with the numbered correction
        if response.isdigit():
            try:
                src_map[error.index] = error.suggestions[int(response)]
                correction = True
            except IndexError:
                print("%sInvalid selection, please try again.%s" % (Back.RED, Style.RESET_ALL))
                return self._handle_response(error)
        # Add word to the excluded words list
        elif response == "a":
            self.dictionary.add(error.word)
        # Next file
        elif response == "n":
            raise NextFile()
        # Stop spellchecking
        elif response == "q":
            raise StopIteration()
        # Ignore the current error by default
        else:
            pass
        return correction

    def _process_file(self, src_file):
        """For each error in the file. Prompt the
        user for the action to take.

        :param src_file: Source file being checked.
        :type src_file: :class:`SourceFile`
        """
        write_file = False
        src_map = self._get_source_map(src_file.content)
        for idx, error in enumerate(src_file.errors()):
            if idx == 0:
                print("\n%s%s:%s\n" % (Fore.GREEN, src_file.relname, Style.RESET_ALL))
            print(error.prompt())
            self._print_options()

            write_file |= self._handle_response(src_map, error)

        if write_file:
            with codecs.open(src_file.filename, 'w', self.encoding) as out_file:
                out_file.write(u''.join(src_map.values()))

    def _get_source_map(self, contents):
        """Creates a map of index, token pairs from the source
        file to handle spelling replacements.

        :param contents: The contents of the source file.
        :returns: The generated map.
        :rtype: :class:`collections.OrderedDict`
        """
        src_map = OrderedDict()
        offset = 0

        for token in re.split(r'(\W+)', contents):
            if token == '':
                continue
            src_map[offset] = token
            offset += len(token)
        return src_map


def get_parser(description=''):
    """Initialise the command line argument parsing.

    :returns: The argument parser.
    :rtype: :class:`argparse.ArgumentParser`
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('--directory', '-d', default='.', help='Base directory to search from')
    parser.add_argument(
        '--interactive', '-i', default=False, action='store_true',
        help='Run the interactive checker'
    )
    parser.add_argument(
        '--ignore-patterns', '-I', nargs='+', default=None, help='List of glob patterns to ignore'
    )
    parser.add_argument('--language', '-l', default='en_GB', help='Language to use')
    parser.add_argument(
        '--excluded-words', '-e', default='.excluded-words', help='Path to excluded words list'
    )
    parser.add_argument('--encoding', '-E', default='utf-8', help='Character encoding to use')
    parser.add_argument('--version', '-v', default=False, action='store_true', help='Print version')

    return parser


def main():
    """Main entry point."""
    parser = get_parser(DESCRIPTION)
    args = parser.parse_args()

    if args.version:
        print(DESCRIPTION)
        print("Version: %s" % _get_version())
    else:
        init()  # Initialise colorama
        checker_class = InteractiveChecker if args.interactive else SpellChecker
        checker = checker_class(args.directory, args.ignore_patterns, args.language,
                                args.excluded_words, args.encoding)
        sys.exit(checker.run())


def _get_version():
    """Read the version from the package metadata."""
    try:
        pkg_info = pkg_resources.get_distribution(NAME)
        return pkg_info.version
    except pkg_resources.DistributionNotFound:
        print("Could not find the distribution information!")
        print(r"The project must be built, and installed with 'pip install' or 'setup.py develop'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
