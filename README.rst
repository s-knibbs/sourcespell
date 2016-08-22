SourceSpell
===========

.. image:: https://travis-ci.org/s-knibbs/sourcespell.svg?branch=master
    :target: https://travis-ci.org/s-knibbs/sourcespell

Command line spellchecking utility for checking comments and string literals in source code files.
Includes an interactive mode for making corrections.

Supports a wide array of languages including Python, C/C++ and HTML markup.

For more information, see the `documentation`_.

Basic Usage
-----------

To print a list of spelling errors for a project::

    sourcespell -d path/to/project [-I file/to/ignore]

Installation
------------

Install with pip::

    pip install sourcespell

Known Issues
------------

The following errors are produced from the enchant library when using an excluded words list::

    ** (process:214): CRITICAL **: enchant_is_all_caps: assertion 'word && *word' failed

This is caused by blank-lines in the excluded words file.

.. _documentation: https://s-knibbs.github.io/sourcespell
