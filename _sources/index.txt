.. sourcespell documentation master file, created by
   sphinx-quickstart on Wed Aug 17 17:58:09 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SourceSpell 
===========

Command line spell-checker for source code files. Includes an interactive mode
for quickly fixing spelling errors.

It uses the excellent `Pygments`_ library for parsing and `PyEnchant`_ for spell-checking.
The checker checks for spelling errors in code comments, HTML markup and Python doc comments.
It supports the full list of `languages supported by Pygments`_.

Similar Projects
----------------

`pysource-spellchecker`_
    Also uses *enchant*. Only supports spellchecking of Python.

`codespell`_
    Pure Python checker. Analyses entire source files, in addition to comments.

Contents
--------
.. toctree::
   :maxdepth: 4

   installation
   usage
   sourcespell

.. _PyEnchant: http://pythonhosted.org/pyenchant/
.. _Pygments: http://pygments.org/
.. _languages supported by Pygments: http://pygments.org/languages/
.. _pysource-spellchecker: https://pypi.python.org/pypi/pysource-spellchecker
.. _codespell: https://pypi.python.org/pypi/codespell/1.9.2
