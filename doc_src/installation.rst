Installation
============

Installation is standard::

    pip install SourceSpell

**Note:** For windows, you will also need to `manually install PyEnchant`_
using the pre-built installer which will install the spell-checking backend.

Building from source
--------------------

You can also build and install from source::

    $ git clone https://github.com/s-knibbs/sourcespell

In the checkout directory::

    $ pip install -r requirements.txt
    $ ./setup.py develop

.. _manually install PyEnchant: https://pypi.python.org/pypi/pyenchant/
