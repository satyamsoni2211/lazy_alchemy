import pytest
from sqlalchemy import create_engine, Column, String, Integer, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine

Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    username = Column("username", String(20), primary_key=True)
    age = Column("age", Integer)
    __table_args__ = (Index("idx_user_username", "username"),)


@pytest.fixture
def engine():
    """Create a test engine with a User table."""
    e = create_engine("sqlite:///test.db", echo=False)
    with e.begin() as c:
        Base.metadata.drop_all(bind=c)
        Base.metadata.create_all(bind=c)
    yield e
    e.dispose()


@pytest.fixture
def async_engine():
    """Create an async test engine with a User table."""
    e = create_async_engine("sqlite+aiosqlite:///test_async.db", echo=False)

    async def setup():
        async with e.begin() as c:
            await c.run_sync(Base.metadata.drop_all)
            await c.run_sync(Base.metadata.create_all)

    import asyncio
    asyncio.run(setup())
    yield e
    import asyncio
    asyncio.run(e.dispose())


def create_test_db():
    """Helper to create test DB for direct use."""
    e = create_engine("sqlite:///test.db", echo=False)
    with e.begin() as c:
        Base.metadata.drop_all(bind=c)
        Base.metadata.create_all(bind=c)
    return e


async def create_async_test_db():
    """Helper to create async test DB for direct use."""
    e = create_async_engine("sqlite+aiosqlite:///test_async.db", echo=False)

    async def setup():
        async with e.begin() as c:
            await c.run_sync(Base.metadata.drop_all)
            await c.run_sync(Base.metadata.create_all)

    await setup()
    return e