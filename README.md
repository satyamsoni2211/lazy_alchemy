# 🅛🅐🅩🅨-🅐🅛🅒🅗🅔🅜🅨

*Lazy-Alchemy* is a Python package that loads the database models lazily. It's a wrapper on top of sqlalchemy, so the Lazy-Alchemy can be used with any framework or project that use sqlalchemy.

Sqlalchemy loads the entire metadata of all models during the application startup, thus increases the app start up time significantly. In projects where there are 100s of database models, the start up time can be in minutes due to loading of models metadata.

Lazy-Alchemy is an attempt to solve the above mentioned problem. Lazy-Alchemy significantly boosts the start up time from minutes to seconds. It also saves memory by only loading the models "on-demand", and not loading every model.



[![Pypi tag](https://img.shields.io/pypi/v/lazy_alchemy.svg?style=flat-square&label=version)](https://pypi.org/project/lazy_alchemy/) [![build](https://github.com/joke2k/faker/workflows/Python%20Tests/badge.svg?branch=master&event=push)](https://github.com/satyamsoni2211/lazy_alchemy/actions) [![Licence](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://github.com/satyamsoni2211/lazy_alchemy/blob/master/LICENSE)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/lazy_alchemy)
![GitHub repo size](https://img.shields.io/github/repo-size/satyamsoni2211/lazy_alchemy)
![Codecov](https://img.shields.io/codecov/c/github/satyamsoni2211/lazy_alchemy)
[![CodeFactor](https://www.codefactor.io/repository/github/satyamsoni2211/lazy_alchemy/badge)](https://www.codefactor.io/repository/github/satyamsoni2211/lazy_alchemy)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/satyamsoni2211/lazy_alchemy/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/satyamsoni2211/lazy_alchemy/?branch=master)
[![Code Intelligence Status](https://scrutinizer-ci.com/g/satyamsoni2211/lazy_alchemy/badges/code-intelligence.svg?b=master)](https://scrutinizer-ci.com/code-intelligence)
[![Downloads](https://static.pepy.tech/personalized-badge/lazy-alchemy?period=total&units=abbreviation&left_color=black&right_color=green&left_text=Downloads)](https://pepy.tech/project/lazy-alchemy)
----

### Compatibility


This package is compatible with Python >= 3.6

### Basic Usage


Install with pip:

```bash
    pip install lazy-alchemy
```


```python
    from lazy_alchemy import get_lazy_class
    from sqlalchemy import create_engine

    db_engine = create_engine(DB_CONNECT_STRING)
    lazy_db = get_lazy_class(db_engine)
```

```python
    # SqlAlchemy DB Queries
    db_model = lazy_db.my_db_table_foo

    query = session.query(db_model).filter(db_model.foo == "bar").all()
```

Tests
-----

Run tests:

```bash
    pytest
```


License
-------

Lazy-Alchemy is released under the MIT License. See the bundled [`LICENSE`](https://github.com/satyamsoni2211/lazy_alchemy/blob/master/LICENSE) file
for details.
