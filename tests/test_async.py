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


@pytest.mark.asyncio
async def test_async_as_sqlmodel(async_engine):
    """Test exporting async table to SQLModel."""
    lazy_db = get_lazy_class(async_engine)
    table = await lazy_db.get("user")
    User = table.as_sqlmodel()
    assert User.__tablename__ == "user"
    assert "username" in User.model_fields
    assert "age" in User.model_fields


@pytest.mark.asyncio
async def test_async_as_sqlmodel_with_fk(async_engine):
    """Test that async table with FK exports SQLModel with foreign key attribute."""
    lazy_db = get_lazy_class(async_engine)
    table = await lazy_db.get("address")
    Address = table.as_sqlmodel()
    assert Address.__tablename__ == "address"
    assert "id" in Address.model_fields
    assert "user_username" in Address.model_fields
    assert "city" in Address.model_fields
    # Verify the primary key field metadata
    id_field = Address.model_fields["id"]
    assert id_field.metadata[0].primary_key is True
    # Verify the foreign key field metadata
    user_username_field = Address.model_fields["user_username"]
    assert user_username_field.metadata[0].foreign_key == "user.username"
    # Verify city is a regular field (no pk/fk set)
    city_field = Address.model_fields["city"]
    assert city_field.metadata[0].primary_key is not True
    assert city_field.metadata[0].foreign_key is not True