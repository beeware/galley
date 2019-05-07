Contributing to Galley
======================


If you experience problems with Galley, `log them on GitHub`_. If you want to contribute code, please `fork the code`_ and `submit a pull request`_.

.. _log them on Github: https://github.com/beeware/galley/issues
.. _fork the code: https://github.com/beeware/galley
.. _submit a pull request: https://github.com/beeware/galley/pulls


Setting up your development environment
---------------------------------------

The recommended way of setting up your development envrionment for Galley
is to install a virtual environment, install the required dependencies and
start coding. Assuming that you are using ``virtualenvwrapper``, you only have
to run::

    $ git clone git@github.com:beeware/galley.git
    $ cd galley
    $ mkvirtualenv galley

Galley uses ``unittest`` (or ``unittest2`` for Python < 2.7) for its own test
suite as well as additional helper modules for testing. To install all the
requirements for Galley, you have to run the following commands within your
virutal envrionment::

    $ pip install -e .
    $ pip install -r requirements_dev.txt

Now you are ready to start hacking! Have fun!
