#!/usr/bin/env python
from setuptools import setup
from distutils.command.upload import upload as _upload

import codecs
from getpass import getpass


def read(filename):
    return codecs.open(filename).read()


LONG_DESCRIPTION = read('README.rst')
VERSION = '1.1'


class upload(_upload):
    """Override the upload command
    to workaround https://bugs.python.org/issue18454
    """

    def run(self):
        if self.password is None:
            self.password = getpass()
        _upload.run(self)


setup(
    cmdclass={'upload': upload},
    name='SourceSpell',
    version=VERSION,
    url='https://s-knibbs.github.io/sourcespell',
    download_url='https://github.com/s-knibbs/sourcespell/tarball/%s' % VERSION,
    license='GPLv3',
    author='Simon J Knibbs',
    author_email='simon.knibbs@gmail.com',
    description='Command line spellchecker for source code files.',
    long_description=LONG_DESCRIPTION,
    packages=['sourcespell'],
    platforms='any',
    install_requires=[
        'pyenchant>=1.6.7',
        'Pygments>=2.0.2',
        'colorama>=0.3.3',
        'python-magic>=0.4.12'
    ],
    classifiers=[
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Quality Assurance'
    ],
    entry_points={
        'console_scripts': [
            'sourcespell = sourcespell.sourcespell:main'
        ]
    }
)
