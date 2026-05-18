import pytest
from tests.conftest import create_test_db
from lazy_alchemy import get_lazy_class, CustomTable, TableNotFoundError
from sqlalchemy import Column


def test_lazy_class_returns_table():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    table = lazy_db.user
    assert isinstance(table, CustomTable)
    assert table.name == "user"


def test_table_not_found_raises_custom_error():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    with pytest.raises(TableNotFoundError):
        _ = lazy_db.nonexistent_table


def test_column_access_via_delegation():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    table = lazy_db.user
    assert isinstance(table.username, Column)
    assert isinstance(table.age, Column)


def test_constraint_and_index():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    table = lazy_db.user
    assert len(table.constraints) == 1
    assert any(i.name == "idx_user_username" for i in table.indexes)


def test_custom_table_bool():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    table = lazy_db.user
    assert bool(table) is True


def test_table_caching():
    """Tables should be cached and return the same instance."""
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    table1 = lazy_db.user
    table2 = lazy_db.user
    assert table1 is table2


def test_list_tables():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    tables = lazy_db.list_tables()
    assert "user" in tables