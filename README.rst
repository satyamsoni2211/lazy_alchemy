*Lazy-Alchemy* is a Python package that loads the database models lazily. It's a wrapper on top of sqlalchemy, so the Lazy-Alchemy can be used with any framework or project that use sqlalchemy.

Sqlalchemy loads the entire metadata of all models during the application startup, thus increases the app start up time significantly. In projects where there are 100s of database models, the start up time can be in minutes due to loading of models metadata.

Lazy-Alchemy is an attempt to solve the above mentioned problem. Lazy-Alchemy significantly boosts the start up time from minutes to seconds. It also saves memory by only loading the models "on-demand", and not loading every model.

----

::

🅛🅐🅩🅨-🅐🅛🅒🅗🅔🅜🅨


|pypi| |build| |coverage| |license|

----

Compatibility
-------------

This package is compatible with Python >= 3.6

Basic Usage
-----------

Install with pip:

.. code:: bash

    pip install lazy-alchemy


.. code:: python

    from lazy_alchemy import get_lazy_class
    from sqlalchemy import create_engine

    db_engine = create_engine(DB_CONNECT_STRING)
    lazy_db = get_lazy_class(db_engine)


.. code:: python

    # SqlAlchemy DB Queries
    db_model = lazy_db.my_db_table_foo

    query = session.query(db_model).filter(db_model.foo == "bar").all()


Tests
-----

Run tests:

.. code:: bash

    $ pytest .


License
-------

Lazy-Alchemy is released under the MIT License. See the bundled `LICENSE`_ file
for details.

Credits
-------
.. _LICENSE: https://github.com/satyamsoni2211/lazy_alchemy/blob/master/LICENSE

.. |pypi| image:: https://img.shields.io/pypi/v/lazy_alchemy.svg?style=flat-square&label=version
    :target: https://pypi.org/project/lazy_alchemy/
    :alt: Latest version released on PyPI

.. |coverage| image::
    :target:
    :alt: Test coverage

.. |build| image:: https://github.com/joke2k/faker/workflows/Python%20Tests/badge.svg?branch=master&event=push
    :target: https://github.com/satyamsoni2211/lazy_alchemy/actions
    :alt: Build status of the master branch on Mac/Linux

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square
    :target: https://github.com/satyamsoni2211/lazy_alchemy/blob/master/LICENSE
    :alt: Package license