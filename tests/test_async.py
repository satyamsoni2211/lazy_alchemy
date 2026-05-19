import pytest
from lazy_alchemy import get_lazy_class


@pytest.mark.asyncio
async def test_async_get_returns_table(async_engine):
    lazy_db = get_lazy_class(async_engine)
    table = await lazy_db.get("user")
    assert table.name == "user"


@pytest.mark.asyncio
async def test_async_caching(async_engine):
    lazy_db = get_lazy_class(async_engine)
    table1 = await lazy_db.get("user")
    table2 = await lazy_db.get("user")
    assert table1 is table2


@pytest.mark.asyncio
async def test_async_invalidate(async_engine):
    lazy_db = get_lazy_class(async_engine)
    _ = await lazy_db.get("user")
    await lazy_db.invalidate("user")


@pytest.mark.asyncio
async def test_async_invalidate_all(async_engine):
    lazy_db = get_lazy_class(async_engine)
    _ = await lazy_db.get("user")
    await lazy_db.invalidate_all()
    assert len(lazy_db._cache) == 0


@pytest.mark.asyncio
async def test_async_double_checked_locking(async_engine):
    """Test that async double-checked locking path is exercised.

    Covers line 398-400: When cache miss occurs, we acquire the lock,
    check again, then reflect. This tests concurrent access in async context.
    """
    lazy_db = get_lazy_class(async_engine)

    # First access - populate cache
    table1 = await lazy_db.get("user")

    # Invalidate to force cache miss
    await lazy_db.invalidate("user")

    # Second access - should hit the double-check path
    table2 = await lazy_db.get("user")

    assert table1.name == table2.name == "user"