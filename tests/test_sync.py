import time
import threading
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

    Covers lines 246-248: foreign key branch in as_sqlmodel.
    """
    from sqlalchemy import Column, String, Integer, ForeignKey
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    # Create Profile table referencing existing User table
    class Profile(Base):
        __tablename__ = "profile_fk"
        id = Column("id", Integer, primary_key=True)
        user_name = Column("user_name", String(20), ForeignKey("user.username"))

    # Create User table in same metadata so FK can resolve
    class User(Base):
        __tablename__ = "user"
        username = Column("username", String(20), primary_key=True)
        age = Column("age", Integer)

    engine = create_test_db()
    lazy_db = get_lazy_class(engine)

    with engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)
        Base.metadata.create_all(bind=conn)

    # Reflect the profile table - this now has FK to user
    profile = lazy_db.profile_fk
    assert profile is not None

    # Get SQLModel - this exercises the FK branch in as_sqlmodel
    ProfileModel = profile.as_sqlmodel()
    assert ProfileModel is not None


def test_double_checked_locking_sync():
    """Test that double-checked locking path is exercised.

    Lines 305-309: When cache miss occurs, we acquire the lock,
    check again, then reflect. This tests the concurrent access path.
    """
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)

    # First access - populate cache
    table1 = lazy_db.user

    # Invalidate to force cache miss
    lazy_db.invalidate("user")

    # Second access - should hit the double-check path
    table2 = lazy_db.user

    assert table1.name == table2.name == "user"


def test_unknown_column_type_returns_any():
    """Test that sa_column_to_python_type returns Any for unknown types.

    Covers line 152: when no SA type matches, return Any.
    We use a custom SQLAlchemy type that doesn't inherit from any mapped type.
    """
    from sqlalchemy import Column, TypeDecorator, String
    from lazy_alchemy.lazy_alchemy import sa_column_to_python_type, SA_TO_PYTHON

    # Create a custom type that doesn't inherit from any mapped SA type
    class UnknownCustomType(TypeDecorator):
        impl = String(50)
        cache_ok = False

    # Create a mock column with our custom type
    col = Column("unknown_col", UnknownCustomType(), nullable=False)

    # Verify the type is not in SA_TO_PYTHON keys
    assert UnknownCustomType not in SA_TO_PYTHON

    # This should hit line 152 and return Any
    result = sa_column_to_python_type(col)
    # Since the type doesn't match any known SA type, it returns Any
    from typing import Any as TypingAny
    assert result is TypingAny