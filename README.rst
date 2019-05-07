.. image:: https://beeware.org/project/projects/tools/galley/galley.png
    :width: 72px
    :target: https://beeware.org/galley

Galley
======

.. image:: https://img.shields.io/pypi/pyversions/galley.svg
    :target: https://pypi.python.org/pypi/galley

.. image:: https://img.shields.io/pypi/v/galley.svg
    :target: https://pypi.python.org/pypi/galley

.. image:: https://img.shields.io/pypi/status/galley.svg
    :target: https://pypi.python.org/pypi/galley

.. image:: https://img.shields.io/pypi/l/galley.svg
    :target: https://github.com/pybee/galley/blob/master/LICENSE

.. image:: https://travis-ci.org/pybee/galley.svg?branch=master
    :target: https://travis-ci.org/pybee/galley

.. image:: https://badges.gitter.im/pybee/general.svg
    :target: https://gitter.im/pybee/general

GUI tool to assist in drafting documentation.

Quickstart
----------

In your virtualenv, install Galley, and then run it::

    $ pip install galley
    $ galley

This will pop up a GUI window.

Problems under Ubuntu
~~~~~~~~~~~~~~~~~~~~~

Ubuntu's packaging of Python omits the ``idlelib`` library from it's base
packge. If you're using Python 2.7 on Ubuntu 13.04, you can install
``idlelib`` by running::

    $ sudo apt-get install idle-python2.7

For other versions of Python and Ubuntu, you'll need to adjust this as
appropriate.

Problems under Windows
~~~~~~~~~~~~~~~~~~~~~~

If you're running Galley in a virtualenv, you'll need to set an
environment variable so that Galley can find the TCL graphics library::

    $ set TCL_LIBRARY=c:\Python27\tcl\tcl8.5

You'll need to adjust the exact path to reflect your local Python install.
You may find it helpful to put this line in the ``activate.bat`` script
for your virtual environment so that it is automatically set whenever the
virtualenv is activated.

Documentation
-------------

Documentation for Galley can be found on `Read The Docs`_.

Community
---------

Galley is part of the `BeeWare suite`_. You can talk to the community through:

* `@pybeeware on Twitter`_

* The `pybee/general`_ channel on Gitter.

We foster a welcoming and respectful community as described in our
`BeeWare Community Code of Conduct`_.

Contributing
------------

If you experience problems with Galley, `log them on GitHub`_. If you
want to contribute code, please `fork the code`_ and `submit a pull request`_.

.. _BeeWare suite: http://pybee.org
.. _Read The Docs: https://galley.readthedocs.io
.. _@pybeeware on Twitter: https://twitter.com/pybeeware
.. _pybee/general: https://gitter.im/pybee/general
.. _BeeWare Community Code of Conduct: http://pybee.org/community/behavior/
.. _log them on Github: https://github.com/pybee/galley/issues
.. _fork the code: https://github.com/pybee/galley
.. _submit a pull request: https://github.com/pybee/galley/pulls
