
[![Galley](https://beeware.org/project/projects/tools/galley/galley.png)](https://beeware.org/galley)

# Galley

[![Galley](https://img.shields.io/pypi/pyversions/galley.svg)](https://pypi.python.org/pypi/galley)
[![Galley](https://img.shields.io/pypi/v/galley.svg)](https://pypi.python.org/pypi/galley)
[![Galley](https://img.shields.io/pypi/status/galley.svg)](https://pypi.python.org/pypi/galley)
[![Build Status](https://img.shields.io/pypi/l/galley.svg)](https://github.com/pybee/galley/blob/main/LICENSE)
[![Discord server](https://img.shields.io/discord/836455665257021440?label=Discord%20Chat&logo=discord&style=plastic)](https://github.com/beeware/galley/actions)

GUI tool to assist in drafting documentation.

## Quickstart

In your virtualenv, install Galley, and then run it:

```text
pip install galley
```

```text
galley
```

This will pop up a GUI window.

### Problems under Ubuntu

Ubuntu's packaging of Python omits the `idlelib` library from it's base
packge. If you're using Python 2.7 on Ubuntu 13.04, you can install
`idlelib` by running:

```text
sudo apt-get install idle-python2.7
```

For other versions of Python and Ubuntu, you'll need to adjust this as
appropriate.

### Problems under Windows

If you're running Galley in a virtualenv, you'll need to set an
environment variable so that Galley can find the TCL graphics library:

```text
set TCL_LIBRARY=c:\Python27\tcl\tcl8.5
```

You'll need to adjust the exact path to reflect your local Python install.
You may find it helpful to put this line in the `activate.bat` script
for your virtual environment so that it is automatically set whenever the
virtualenv is activated.

## Documentation

Documentation for Galley can be found on [Read The Docs](https://galley.readthedocs.io).

## Community

Galley is part of the [BeeWare suite](https://beeware.org). You can talk to the
community through:

- [@beeware@fosstodon.org on Mastodon](https://fosstodon.org/@beeware)

- [Discord ](https://beeware.org/bee/chat/)

We foster a welcoming and respectful community as described in our
[BeeWare Community Code of Conduct](https://beeware.org/community/behavior/).

## Contributing

If you experience problems with Galley, [log them on GitHub](https://github.com/beeware/galley/issues).

If you want to contribute, please [fork the project](https://github.com/beeware/galley)
and [submit a pull request](https://github.com/beeware/galley/pulls).
