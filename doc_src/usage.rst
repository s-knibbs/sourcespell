Usage
=====

.. argparse::
    :module: sourcespell.sourcespell
    :func: get_parser
    :prog: sourcespell

The checker will automatically skip over hidden (``./*``) files and common binary files, including::

    *.zip, *.jpg, *.png, *.gif, *.gz

If a relative path is given for the excluded-words dictionary, this will be generated relative to the
base directory.

All files will be opened with the same character encoding, so to avoid encoding errors, all files under the base directory should use the same character encoding.

By default, the checker will list all spelling-errors found in each file. If spelling-errors are found
or other errors such as character-encoding and parsing errors, the checker will return non-zero.

Interactive Usage
^^^^^^^^^^^^^^^^^

The following prompt will be generated for each spelling error in interactive mode::

    example.py:

        # This is a line with a **spulling** error.

        0: spilling | 1: spelling | 2: pulling | 3: spieling | 4: sculling | 5: spoiling

        0-9 - Use the numbered suggestion.
        a - Ignore the error and add to the excluded words.
        n - Go to the next file, save existing changes.
        q - Exit immediately, discards changes in the current file.
        To skip to the next error, press any other key.
        --->

**Note:** The suggestions provided will depend on the spell-checking backend (Hunspell, Aspell, ...) in use.

