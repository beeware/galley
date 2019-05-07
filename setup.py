#!/usr/bin/env python
from setuptools import setup

from galley import VERSION

try:
    readme = open('README.rst')
    long_description = str(readme.read())
finally:
    readme.close()

required_pkgs = ['tkreadonly', 'sphinx']

setup(
    name='galley',
    version=VERSION,
    description='GUI tool to assist in drafting documentation.',
    long_description=long_description,
    author='Russell Keith-Magee',
    author_email='russell@keith-magee.com',
    url='http://pybee.org/galley',
    packages=[
        'galley',
    ],
    install_requires=required_pkgs,
    entry_points={
        'console_scripts': [
            'galley = galley.__main__:main',
        ]
    },
    license='New BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development',
        'Topic :: Utilities',
    ],
    test_suite='tests'
)
