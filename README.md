<div align="center">

# lazy-alchemy

**On-demand SQLAlchemy table reflection — zero startup cost, production-ready caching.**

[![PyPI](https://img.shields.io/pypi/v/lazy-alchemy?color=4f46e5&labelColor=1e1b4b)](https://pypi.org/project/lazy-alchemy/)
[![Python](https://img.shields.io/pypi/pyversions/lazy-alchemy?color=4f46e5&labelColor=1e1b4b)](https://pypi.org/project/lazy-alchemy/)
[![Build](https://img.shields.io/github/actions/workflow/status/satyamsoni2211/lazy_alchemy/python-package.yml?branch=master&color=4f46e5&labelColor=1e1b4b)](https://github.com/satyamsoni2211/lazy_alchemy/actions)
[![Coverage](https://img.shields.io/codecov/c/github/satyamsoni2211/lazy_alchemy?color=4f46e5&labelColor=1e1b4b)](https://codecov.io/gh/satyamsoni2211/lazy_alchemy)
[![License](https://img.shields.io/github/license/satyamsoni2211/lazy_alchemy?color=4f46e5&labelColor=1e1b4b)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/lazy-alchemy?color=4f46e5&labelColor=1e1b4b)](https://pepy.tech/project/lazy-alchemy)

<br/>

</div>

```python
# Before: every table reflected at startup — even the ones you never touch
engine = create_engine(DATABASE_URL)        # ← hundreds of tables loaded

# After: only the tables you actually use, only when you use them
lazy_db = get_lazy_class(engine)
table   = lazy_db.users                     # ← reflected here, on first access
```

---

## Why lazy-alchemy?

SQLAlchemy reflects every table in your database when metadata is loaded at startup. In large schemas — think 100+ tables across microservices or multi-tenant systems — this can stretch application startup from seconds into **minutes**, and waste memory on models you may never query.

`lazy-alchemy` defers reflection entirely. Tables are loaded from the database the first time you access them, then cached. Your app starts instantly. The rest just works.

**v2.0.0** is a complete modernisation: SQLAlchemy 2.x support, native `asyncio`, Pydantic v2 schema generation, SQLModel integration, thread-safe caching with TTL, and full type stubs.

---

## Architecture

The diagram below shows how all components relate — from the unified `get_lazy_class` entry point, through the sync and async engine paths, down through the shared module-level cache and SA2 reflection layer, to the `CustomTable` output methods.

![lazy-alchemy v2 component architecture](assets/images/lazy_alchemy_v2_architecture.svg)

The lifecycle diagram shows exactly what happens at runtime on every table access — the fast cache hit path, the full reflection path (with `TableNotFoundError` guard) when the cache misses, and the parallel async path.

![lazy-alchemy v2 request lifecycle](assets/images/lazy_alchemy_v2_request_lifecycle.svg)

---

## Installation

```bash
pip install lazy-alchemy
```

**Requires:** Python ≥ 3.10 · SQLAlchemy ≥ 2.0 · Pydantic ≥ 2.0 · SQLModel ≥ 0.0.16

All features — async support, Pydantic schema generation, and SQLModel integration — are included in the base install.

For development and testing:

```bash
pip install "lazy-alchemy[dev]"
```

---

## Quick start

### Sync

```python
from lazy_alchemy import get_lazy_class
from sqlalchemy import create_engine, select

engine  = create_engine("postgresql://user:pass@localhost/mydb")
lazy_db = get_lazy_class(engine)

# Table is reflected once, on first access, then cached
users = lazy_db.users

with engine.connect() as conn:
    rows = conn.execute(select(users).where(users.c.active == True)).all()
```

### Async

```python
from lazy_alchemy import get_lazy_class
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select

engine  = create_async_engine("postgresql+asyncpg://user:pass@localhost/mydb")
lazy_db = get_lazy_class(engine)       # detects AsyncEngine automatically

async def get_users(session: AsyncSession):
    users  = await lazy_db.get("users")
    result = await session.execute(select(users))
    return result.mappings().all()
```

The same `get_lazy_class` factory works for both sync and async engines — it auto-detects the engine type and returns the right accessor.

---

## Features

### SQLAlchemy 2.x compatible

`lazy-alchemy` v2 uses the SA2-native reflection API throughout:

```python
# Uses autoload_with=conn (SA2) instead of the removed autoload=True (SA1)
# Uses MetaData() without bind — engines are passed at reflection time
lazy_db = get_lazy_class(engine)
table   = lazy_db.orders              # reflected via autoload_with on first access
```

### Async-native

Pass an `AsyncEngine` and get a non-blocking accessor. Reflection happens inside the event loop with `asyncio.Lock` protection — no thread executor needed.

```python
engine  = create_async_engine("postgresql+asyncpg://...")
lazy_db = get_lazy_class(engine)

# In any async context:
orders = await lazy_db.get("orders")
```

### Pydantic v2 schema generation

Reflect a table and get a validated Pydantic model in one line — column types, nullability, and defaults are all inferred from the live schema.

```python
lazy_db    = get_lazy_class(engine)
UserSchema = lazy_db.users.as_pydantic()

# Full model with type validation
user = UserSchema(id=1, name="Alice", email="alice@example.com")
print(user.model_dump_json())

# Partial schema — all fields Optional, useful for PATCH endpoints
UserPatch = lazy_db.users.as_pydantic_partial()
patch     = UserPatch(name="Alice Updated")   # everything else is None
```

### SQLModel integration

Generate a first-class `SQLModel` class — usable with FastAPI response models, OpenAPI schema generation, and SQLModel sessions.

```python
from sqlmodel import Session, select

User    = lazy_db.users.as_sqlmodel()
session = Session(engine)

# Works as a FastAPI response_model, query target, and Pydantic model
@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    return session.get(User, user_id)
```

### Thread-safe caching with TTL

Reflected tables are stored in a **module-level cache** shared across all instances for the same engine. A double-checked lock prevents duplicate reflection under concurrent load.

```python
# Re-reflect tables after 5 minutes (useful after live migrations)
lazy_db = get_lazy_class(engine, cache_ttl=300)

# Force a specific table to re-reflect on next access
lazy_db.invalidate("users")

# Wipe the entire cache for this engine
lazy_db.invalidate_all()

# Warm the cache at startup for your hottest tables
lazy_db.preload("users", "orders", "products")
```

### Multi-schema support

```python
# PostgreSQL schema namespacing
public_db    = get_lazy_class(engine, schema="public")
analytics_db = get_lazy_class(engine, schema="analytics")

users  = public_db.users
events = analytics_db.events
```

### Table introspection

```python
# List every table in the schema
lazy_db.list_tables()
# → ['users', 'orders', 'products', 'order_items', ...]

# Column access via attribute delegation
table = lazy_db.users
print(table.email)     # equivalent to table.c.email
```

### Meaningful errors

```python
lazy_db.nonexistent_table
# TableNotFoundError: Table 'nonexistent_table' not found in database 'mydb'.
# Available tables: order_items, orders, products, users
```

### Full type safety

The package ships a `py.typed` marker and typed stubs (`__init__.pyi`), so mypy and pyright understand the full API surface with no extra configuration.

```python
# mypy / pyright understand all of this:
lazy_db : LazyDB              = get_lazy_class(sync_engine)
accessor: AsyncLazyDBAccessor = get_lazy_class(async_engine)
table   : CustomTable         = lazy_db.users
schema  : type[BaseModel]     = table.as_pydantic()
```

---

## API reference

### `get_lazy_class(engine, *, cache_ttl=None, schema=None)`

Unified factory. Returns a `LazyDB` for sync engines and an `AsyncLazyDBAccessor` for async engines.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `engine` | `Engine \| AsyncEngine` | — | SQLAlchemy engine |
| `cache_ttl` | `float \| None` | `None` | Seconds before a cached table is re-reflected. `None` = never expire. |
| `schema` | `str \| None` | `None` | Database schema name (e.g. `"analytics"` for PostgreSQL). |

### `LazyDB` (sync)

| Method / attribute | Description |
|---|---|
| `lazy_db.<table_name>` | Reflect and return `CustomTable`, cached after first access. |
| `lazy_db.list_tables()` | Return all table names in the schema. |
| `lazy_db.preload(*names)` | Eagerly reflect tables — useful to warm the cache at startup. |
| `lazy_db.invalidate(name)` | Remove one table from the cache. |
| `lazy_db.invalidate_all()` | Remove all tables for this engine from the cache. |

### `AsyncLazyDBAccessor` (async)

| Method | Description |
|---|---|
| `await lazy_db.get(name)` | Reflect and return `CustomTable`, cached after first call. |
| `await lazy_db.invalidate(name)` | Remove one table from the cache. |
| `await lazy_db.invalidate_all()` | Clear the entire cache. |

### `CustomTable`

A `sqlalchemy.Table` subclass with extra convenience methods.

| Method | Description |
|---|---|
| `table.<column>` | Shorthand for `table.c.<column>` — direct column access by name. |
| `table.as_pydantic(partial=False)` | Generate a Pydantic v2 `BaseModel` from the reflected schema. |
| `table.as_pydantic_partial()` | Generate a Pydantic model with all fields `Optional`. |
| `table.as_sqlmodel()` | Generate a `SQLModel` class from the reflected schema. |

### Exceptions

```python
from lazy_alchemy import LazyAlchemyError, TableNotFoundError, ReflectionError
```

| Exception | Raised when |
|---|---|
| `TableNotFoundError` | The accessed table name does not exist in the database. |
| `ReflectionError` | Reflection succeeded but the resulting metadata is invalid. |
| `LazyAlchemyError` | Base class — catch this to handle any lazy-alchemy error. |

---

## Recipes

### FastAPI with async sessions

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from lazy_alchemy import get_lazy_class

engine       = create_async_engine("postgresql+asyncpg://user:pass@localhost/mydb")
lazy_db      = get_lazy_class(engine)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the cache for your hottest tables at startup
    await lazy_db.get("users")
    await lazy_db.get("orders")
    yield

app = FastAPI(lifespan=lifespan)

async def get_session():
    async with SessionLocal() as session:
        yield session

@app.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    users  = await lazy_db.get("users")
    result = await session.execute(select(users).where(users.c.id == user_id))
    return result.mappings().first()
```

### CRUD endpoints with Pydantic schemas

```python
from lazy_alchemy import get_lazy_class
from sqlalchemy import create_engine

engine  = create_engine("postgresql://user:pass@localhost/mydb")
lazy_db = get_lazy_class(engine)

# Full schema for POST / response model
UserCreate = lazy_db.users.as_pydantic()

# Partial schema for PATCH — only provided fields are updated
UserUpdate = lazy_db.users.as_pydantic_partial()

@app.post("/users", response_model=UserCreate)
def create_user(body: UserCreate): ...

@app.patch("/users/{user_id}", response_model=UserCreate)
def update_user(user_id: int, body: UserUpdate): ...
```

### Cache invalidation after migrations

```python
from alembic import context

def run_migrations_online():
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()

    # Invalidate after migration so next access re-reflects new schema
    lazy_db.invalidate_all()
```

### Working with multiple schemas

```python
engine = create_engine("postgresql://user:pass@localhost/mydb")

public    = get_lazy_class(engine, schema="public")
reporting = get_lazy_class(engine, schema="reporting")
archive   = get_lazy_class(engine, schema="archive")

# Each accessor has its own isolated cache
users         = public.users
monthly_sales = reporting.monthly_sales
legacy_orders = archive.orders_2019
```

---

## Migrating from v1

v2 requires SQLAlchemy 2.x. If you are still on SQLAlchemy 1.4, stay on `lazy-alchemy` v1 until you are ready to upgrade both at the same time.

```python
# v1 — still works, no changes needed on your side
from lazy_alchemy import get_lazy_class
from sqlalchemy import create_engine

lazy_db  = get_lazy_class(create_engine(DB_URL))
db_model = lazy_db.my_table
rows     = session.query(db_model).filter(db_model.foo == "bar").all()
```

When you upgrade to SQLAlchemy 2.x, the new-style query API is recommended:

```python
# SQLAlchemy 2.x style
from sqlalchemy import select

rows = session.execute(
    select(db_model).where(db_model.c.foo == "bar")
).all()
```

### What changed in v2

| Area | v1 | v2 |
|---|---|---|
| SA compatibility | SA 1.x only | SA 2.x (required) |
| Async | ✗ | ✓ `AsyncEngine` + `asyncio.Lock` |
| Pydantic | ✗ | ✓ `as_pydantic()`, `as_pydantic_partial()` |
| SQLModel | ✗ | ✓ `as_sqlmodel()` |
| Cache | Descriptor-level, per-instance | Module-level, process-shared, TTL, thread-safe |
| Type stubs | ✗ | ✓ `py.typed` + `__init__.pyi` |
| Multi-schema | ✗ | ✓ `schema=` parameter |
| Error messages | SA reflection errors | `TableNotFoundError` with available table list |
| Packaging | `setup.cfg` + `Pipfile` | `pyproject.toml` + `hatchling` |
| Python | ≥ 3.6 | ≥ 3.10 |

---

## Development

```bash
git clone https://github.com/satyamsoni2211/lazy_alchemy
cd lazy_alchemy
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=lazy_alchemy --cov-report=term-missing

# Type checking
mypy lazy_alchemy

# Linting
ruff check lazy_alchemy
```

---

## License

Released under the [MIT License](LICENSE).