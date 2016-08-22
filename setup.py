#!/usr/bin/env python
from setuptools import setup

import codecs
import sourcespell


def read(filename):
    return codecs.open(filename).read()


LONG_DESCRIPTION = read('README.rst')


setup(
    name='SourceSpell',
    version=sourcespell.__version__,
    url='http://github.com/s-knibbs/sourcespell',
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
