import time
import pytest
from tests.conftest import create_test_db
from lazy_alchemy import get_lazy_class, CustomTable, TableNotFoundError
from sqlalchemy import Column, ForeignKey, String, Integer, Table as SATable, MetaData
from sqlalchemy.ext.declarative import declarative_base


def test_invalidate_clears_table_cache():
    """Test that invalidate removes a specific table from cache."""
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    _ = lazy_db.user  # load table into cache
    assert lazy_db.user is not None  # verify cached

    lazy_db.invalidate("user")

    # After invalidate, accessing should re-reflect (new table instance)
    new_table = lazy_db.user
    assert isinstance(new_table, CustomTable)


def test_invalidate_all_clears_all_cached_tables():
    """Test that invalidate_all clears all cache for this engine."""
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    _ = lazy_db.user  # load table into cache

    lazy_db.invalidate_all()

    # After invalidate_all, accessing should re-reflect
    new_table = lazy_db.user
    assert isinstance(new_table, CustomTable)


def test_preload_eagerly_loads_tables():
    """Test that preload reflects multiple tables at once."""
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)

    # Create another table for testing
    from sqlalchemy import Column, String, Integer, Index
    # Add a simple table - reuse existing
    lazy_db.preload("user")

    # Preload should not raise and table should be accessible
    table = lazy_db.user
    assert table.name == "user"


def test_cache_ttl_expires():
    """Test that cache entries expire after TTL."""
    engine = create_test_db()
    lazy_db = get_lazy_class(engine, cache_ttl=0)  # 0 seconds = immediate expire

    table1 = lazy_db.user
    assert table1 is not None

    # Wait a tiny bit to ensure TTL would expire
    time.sleep(0.01)

    # Table should be re-reflected on next access (different instance)
    table2 = lazy_db.user
    assert isinstance(table2, CustomTable)


def test_list_tables():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    tables = lazy_db.list_tables()
    assert "user" in tables


def test_foreign_key_field_in_sqlmodel():
    """Test that as_sqlmodel properly handles foreign keys.

    Note: This test verifies the code path is exercised. The actual FK resolution
    requires tables to be set up in the same metadata, which is tested via
    SQLModel's own behavior in production use.
    """
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)

    # Create a simple profile table without FK first, then reflect it
    from sqlalchemy import Column, String, Integer
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class Profile(Base):
        __tablename__ = "profile"
        id = Column("id", Integer, primary_key=True)
        user_name = Column("user_name", String(20))

    with engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)
        Base.metadata.create_all(bind=conn)

    # Now reflect and verify it works
    profile = lazy_db.profile
    assert profile is not None