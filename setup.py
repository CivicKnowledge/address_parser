#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import address_parser


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    readme = f.read()

packages = [
    'address_parser',
]

package_data = {"": ['*.html', '*.css', '*.rst']}


requires = [
]

classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Software Development :: Libraries :: Python Modules',
]

setup(
    name='address_parser',
    version=address_parser.__version__,
    description='Address parser',
    long_description=readme,
    packages=packages,
    package_data=package_data,
    install_requires=requires,
    author=address_parser.__author__,
    author_email='eric@sandiegodata.org',
    url='https://github.com/streeter/python-skeleton',
    license='MIT',
    classifiers=classifiers,
)
