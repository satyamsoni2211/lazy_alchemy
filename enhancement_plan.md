# lazy_alchemy v2 — Enhancement & Modernisation Plan

> A comprehensive roadmap for evolving `lazy_alchemy` from a SQLAlchemy 1.x utility
into a first-class library for modern Python, with full SQLAlchemy 2, asyncio,
SQLModel, and Pydantic v2 support.
> 

---

## Table of contents

1. [Executive summary](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#1-executive-summary)
2. [Current state analysis](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#2-current-state-analysis)
3. [Breaking compatibility issues](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#3-breaking-compatibility-issues-sqlalchemy-2x)
4. [Phase 1 — SQLAlchemy 2 migration (critical)](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#4-phase-1--sqlalchemy-2-migration-critical)
5. [Phase 2 — Async engine support](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#5-phase-2--async-engine-support)
6. [Phase 3 — Pydantic v2 and SQLModel integration](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#6-phase-3--pydantic-v2-and-sqlmodel-integration)
7. [Phase 4 — Cache architecture overhaul](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#7-phase-4--cache-architecture-overhaul)
8. [Phase 5 — Type safety and IDE integration](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#8-phase-5--type-safety-and-ide-integration)
9. [Phase 6 — Schema-aware features](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#9-phase-6--schema-aware-features)
10. [Phase 7 — Packaging and tooling modernisation](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#10-phase-7--packaging-and-tooling-modernisation)
11. [Proposed public API](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#11-proposed-public-api)
12. [Migration guide (v1 → v2)](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#12-migration-guide-v1--v2)
13. [Priority and effort matrix](https://claude.ai/chat/c198c52d-6908-4564-93e9-e8c8d1caaeee#13-priority-and-effort-matrix)

---

## 1. Executive summary

`lazy_alchemy` solves a real problem: SQLAlchemy loads every table's metadata at
startup, which can cost minutes in large schemas. The library defers this to
first-access, cutting startup time to near-zero.

However, as of v1.0.3 the library is broken against SQLAlchemy 2.x (hard crashes,
not just deprecation warnings), has no async support, produces no typed output, and
lacks the integrations developers expect in 2025 — Pydantic validation, SQLModel
compatibility, thread safety, and a proper packaging story.

This plan lays out a phased approach to address all of these, maintaining full
backwards compatibility for existing sync users while opening the library to
entirely new audiences.

---

## 2. Current state analysis

### Core implementation (v1.0.3)

The entire library is ~50 lines across two files:

```
lazy_alchemy/
├── __init__.py          # re-exports get_lazy_class, CustomTable
├── lazy_alchemy.py      # all logic
└── VERSION              # "1.0.3"
```

**`CustomTable`** subclasses `sqlalchemy.Table` and adds:

- `__getattr__` delegation to `.c` (columns), so `table.foo` works as `table.c.foo`
- `__bool__` returning `self is not None`

**`LazyDBProp`** is a Python descriptor that:

- Stores a single `_table` reference (instance-level cache)
- Triggers `Table(name, metadata, autoload=True)` on first access
- Patches itself onto the dynamic class via `setattr(type(self), attribute, obj)`

**`get_lazy_class(engine)`** is a factory function that:

- Uses `type()` to dynamically construct `LazyClass_{database_name}`
- Binds `__init__`, `__getattr__`, and `__patch` onto the new class
- Returns an instance of that class

### What works well

- Zero-startup-cost model reflection is genuinely useful
- The descriptor approach means the cache is "free" — no extra dict lookups
- Per-engine class naming avoids cross-schema contamination
- Simple API: one function call, then attribute access

### What is broken or missing

| Area | Problem |
| --- | --- |
| SA2 compatibility | `MetaData(engine)` removed; `autoload=True` removed |
| Async | No support for `AsyncEngine` or `AsyncSession` |
| Type safety | `type()` construction is invisible to mypy/pyright |
| Pydantic | Returns raw `Table`, no validation or serialisation |
| SQLModel | No integration with the dominant FastAPI ORM |
| Cache | No TTL, no invalidation, not thread-safe, not process-shared |
| Multi-schema | No support for PostgreSQL schemas or cross-DB reflection |
| Error messages | SA reflection errors are cryptic when tables don't exist |
| Packaging | `setup.cfg` + `setup.py`, no `pyproject.toml`, Python 3.9 cap |

---

## 3. Breaking compatibility issues (SQLAlchemy 2.x)

These are hard crashes — not warnings — on any SA 2.x installation.

### Issue 1: `MetaData(engine)` removed

**Current code:**

```python
def __init__(self, engine: Engine):
    self.metadata = MetaData(engine)   # ← TypeError in SA2
    self.engine = engine
```

**SA2 change:** The `bind` parameter was removed from `MetaData`. Engines are no
longer attached to `MetaData` globally — they are passed at reflection time.

**Fix:**

```python
def __init__(self, engine: Engine):
    self.metadata = MetaData()         # ← no bind
    self.engine = engine
```

### Issue 2: `autoload=True` removed

**Current code:**

```python
self._table = CustomTable(
    self._name, instance.metadata, autoload=True
)
```

**SA2 change:** `autoload=True` is removed. Reflection now requires an explicit
`autoload_with` parameter that receives an engine or connection object.

**Fix:**

```python
with instance.engine.connect() as conn:
    self._table = CustomTable(
        self._name, instance.metadata, autoload_with=conn
    )
```

### Issue 3: `session.query()` in docs

The README example uses `session.query(db_model)`. While this still works in SA2
legacy mode, it is removed from the SA2 2.0 style and will eventually be dropped.
Documentation should demonstrate the `select()` + `session.execute()` pattern.

---

## 4. Phase 1 — SQLAlchemy 2 migration (critical)

**Goal:** Make the library work correctly on SQLAlchemy 2.x without breaking
existing SQLAlchemy 1.4 users.

**Effort:** Low (~1 day)
**Risk:** Very low — changes are localised to `lazy_alchemy.py`

### 4.1 SA version detection

Support both SA 1.4 and SA 2.x with a compatibility shim:

```python
import sqlalchemy
SA2 = int(sqlalchemy.__version__.split(".")[0]) >= 2

class LazyDBProp:
    def __get__(self, instance, _):
        if self._table is None:
            if SA2:
                with instance.engine.connect() as conn:
                    self._table = CustomTable(
                        self._name,
                        instance.metadata,
                        autoload_with=conn,
                    )
            else:
                self._table = CustomTable(
                    self._name,
                    instance.metadata,
                    autoload=True,
                )
        return self._table
```

### 4.2 Table existence guard

Replace the cryptic SA reflection error with a helpful message:

```python
from sqlalchemy import inspect as sa_inspect

def __get__(self, instance, _):
    if self._table is None:
        inspector = sa_inspect(instance.engine)
        available = inspector.get_table_names(schema=instance.schema)
        if self._name not in available:
            raise TableNotFoundError(
                f"Table '{self._name}' not found in database "
                f"'{instance.engine.url.database}'. "
                f"Available tables: {', '.join(sorted(available))}"
            )
        # ... proceed with reflection
```

### 4.3 Custom exception hierarchy

```python
class LazyAlchemyError(Exception):
    """Base exception for lazy_alchemy."""

class TableNotFoundError(LazyAlchemyError):
    """Raised when a requested table does not exist in the schema."""

class ReflectionError(LazyAlchemyError):
    """Raised when table metadata cannot be reflected."""
```

### 4.4 Updated dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "sqlalchemy>=1.4",   # support both SA1.4 and SA2
]

[project.optional-dependencies]
sa2 = ["sqlalchemy>=2.0"]
```

---

## 5. Phase 2 — Async engine support

**Goal:** Allow `lazy_alchemy` to be used with `AsyncEngine` inside asyncio
applications (FastAPI, Litestar, asyncpg, etc.).

**Effort:** Medium (~3 days)
**Risk:** Low — entirely additive, new API surface only

### 5.1 Why async matters

Python descriptors cannot be `async`. A `__get__` that does I/O will block the
event loop. In any `async def` handler, blocking the event loop even for a few
milliseconds causes latency spikes across all concurrent requests.

The fix is a separate async-aware lazy class that exposes an awaitable accessor.

### 5.2 `AsyncLazyDB` design

```python
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection
from sqlalchemy import Table, MetaData

class AsyncLazyDBAccessor:
    """Awaitable table accessor for async contexts."""

    def __init__(self, engine: AsyncEngine, metadata: MetaData):
        self._engine = engine
        self._metadata = metadata
        self._cache: dict[str, Table] = {}
        self._lock = asyncio.Lock()

    async def get(self, table_name: str) -> Table:
        if table_name in self._cache:
            return self._cache[table_name]
        async with self._lock:
            if table_name in self._cache:   # double-checked locking
                return self._cache[table_name]
            async with self._engine.connect() as conn:
                table = await conn.run_sync(
                    lambda sync_conn: Table(
                        table_name,
                        self._metadata,
                        autoload_with=sync_conn,
                    )
                )
            self._cache[table_name] = table
            return table

    def __getattr__(self, name: str):
        """Support await lazy_db.my_table syntax via a coroutine property."""
        return self.get(name)

def get_async_lazy_class(engine: AsyncEngine) -> AsyncLazyDBAccessor:
    """
    Factory for async-compatible lazy table loading.

    Usage:
        engine = create_async_engine(DB_URL)
        lazy_db = get_async_lazy_class(engine)

        # In an async function:
        users = await lazy_db.get("users")
        result = await session.execute(select(users))
    """
    metadata = MetaData()
    return AsyncLazyDBAccessor(engine, metadata)
```

### 5.3 Usage examples

```python
# FastAPI example
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from lazy_alchemy import get_async_lazy_class

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/mydb")
lazy_db = get_async_lazy_class(engine)

app = FastAPI()

@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_session)):
    users_table = await lazy_db.get("users")
    result = await session.execute(select(users_table))
    return result.mappings().all()
```

### 5.4 Unified factory (sync + async)

```python
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

def get_lazy_class(engine: Engine | AsyncEngine):
    """
    Unified factory. Returns the appropriate lazy class based on engine type.

    - Sync Engine  → LazyDB (attribute access, backwards compatible)
    - AsyncEngine  → AsyncLazyDB (awaitable .get() accessor)
    """
    if isinstance(engine, AsyncEngine):
        return get_async_lazy_class(engine)
    return get_sync_lazy_class(engine)
```

---

## 6. Phase 3 — Pydantic v2 and SQLModel integration

**Goal:** Allow the reflected `Table` to be consumed as a Pydantic model or
SQLModel class, enabling validation, serialisation, and OpenAPI schema generation
with zero hand-written schema code.

**Effort:** High (~5 days)
**Risk:** Medium — type mapping has edge cases; ship as optional extras

### 6.1 SQLAlchemy → Pydantic type mapping

The core challenge is mapping SA column types to Python/Pydantic types:

```python
from sqlalchemy import types as sa_types
from typing import Any, Optional
import datetime, decimal, uuid

SA_TO_PYTHON: dict[type, type] = {
    sa_types.Integer:    int,
    sa_types.BigInteger: int,
    sa_types.SmallInteger: int,
    sa_types.Float:      float,
    sa_types.Numeric:    decimal.Decimal,
    sa_types.String:     str,
    sa_types.Text:       str,
    sa_types.Unicode:    str,
    sa_types.Boolean:    bool,
    sa_types.Date:       datetime.date,
    sa_types.DateTime:   datetime.datetime,
    sa_types.Time:       datetime.time,
    sa_types.Interval:   datetime.timedelta,
    sa_types.LargeBinary: bytes,
    sa_types.JSON:       Any,
    sa_types.UUID:       uuid.UUID,
}

def sa_column_to_python_type(column) -> type:
    for sa_type, py_type in SA_TO_PYTHON.items():
        if isinstance(column.type, sa_type):
            return Optional[py_type] if column.nullable else py_type
    return Any  # fallback for unknown types
```

### 6.2 `CustomTable.as_pydantic()` method

```python
from pydantic import BaseModel, create_model
from typing import Optional

class CustomTable(Table):
    def as_pydantic(self, *, partial: bool = False) -> type[BaseModel]:
        """
        Generate a Pydantic v2 model from this table's reflected schema.

        Args:
            partial: If True, all fields are Optional (useful for PATCH endpoints).

        Returns:
            A dynamically created Pydantic BaseModel subclass.

        Example:
            UserSchema = lazy_db.users.as_pydantic()
            user = UserSchema(id=1, name="Alice", email="alice@example.com")
            print(user.model_json_schema())
        """
        fields = {}
        for col in self.columns:
            py_type = sa_column_to_python_type(col)
            if partial:
                py_type = Optional[py_type]
                default = None
            else:
                default = col.default.arg if col.default else ...
            fields[col.name] = (py_type, default)

        return create_model(
            f"{self.name.title().replace('_', '')}Schema",
            **fields
        )

    def as_pydantic_partial(self) -> type[BaseModel]:
        """Convenience method: all fields Optional. Use for PATCH/UPDATE endpoints."""
        return self.as_pydantic(partial=True)
```

### 6.3 SQLModel integration (optional extra)

SQLModel combines Pydantic and SQLAlchemy ORM. The integration creates a proper
`SQLModel` table class from reflected metadata:

```python
# Only available when sqlmodel is installed
# pip install lazy-alchemy[sqlmodel]

from sqlmodel import SQLModel, Field
from typing import Optional

class CustomTable(Table):
    def as_sqlmodel(self) -> type[SQLModel]:
        """
        Generate a SQLModel class from reflected schema.

        The returned class can be used directly with SQLModel sessions,
        FastAPI response models, and OpenAPI schema generation.

        Example:
            User = lazy_db.users.as_sqlmodel()

            # Use with FastAPI
            @app.get("/users/{user_id}", response_model=User)
            def get_user(user_id: int, session: Session = Depends(get_session)):
                return session.get(User, user_id)
        """
        try:
            from sqlmodel import SQLModel, Field
        except ImportError:
            raise ImportError(
                "sqlmodel is required for as_sqlmodel(). "
                "Install it with: pip install lazy-alchemy[sqlmodel]"
            )

        fields = {}
        annotations = {}

        for col in self.columns:
            py_type = sa_column_to_python_type(col)
            default = col.default.arg if col.default else None

            if col.primary_key:
                fields[col.name] = Field(default=default, primary_key=True)
            elif col.foreign_keys:
                fk = next(iter(col.foreign_keys))
                fields[col.name] = Field(default=default, foreign_key=str(fk.target_fullname))
            else:
                fields[col.name] = Field(default=default)

            annotations[col.name] = py_type

        namespace = {"__annotations__": annotations, "__tablename__": self.name}
        namespace.update(fields)

        return type(
            self.name.title().replace("_", ""),
            (SQLModel, table=True),
            namespace,
        )
```

### 6.4 Usage examples

```python
# Pydantic validation
UserSchema = lazy_db.users.as_pydantic()
user = UserSchema(id=1, name="Alice", email="alice@example.com")
print(user.model_dump_json())

# Partial schema for PATCH endpoints
UserPatch = lazy_db.users.as_pydantic_partial()
patch = UserPatch(name="Alice Updated")  # only name, everything else Optional

# SQLModel for full ORM + FastAPI integration
User = lazy_db.users.as_sqlmodel()

@app.get("/users", response_model=list[User])
async def list_users(session: Session = Depends(get_session)):
    return session.exec(select(User)).all()
```

---

## 7. Phase 4 — Cache architecture overhaul

**Goal:** Make caching production-grade: thread-safe, process-shared, TTL-aware,
and explicitly invalidatable.

**Effort:** Low-Medium (~2 days)
**Risk:** Low

### 7.1 Problems with the current cache

| Problem | Impact |
| --- | --- |
| Instance-level cache (on descriptor `_table`) | Multiple `get_lazy_class()` calls reflect the same table repeatedly |
| No TTL | Stale after migrations in long-running processes |
| No invalidation | Cannot force refresh without restarting the process |
| Not thread-safe | TOCTOU race: two threads can both see `_table is None` and double-reflect |
| No async safety | `asyncio.Lock` not used, so concurrent coroutines can race |

### 7.2 Module-level shared cache

```python
import threading
from weakref import WeakValueDictionary

_TABLE_CACHE: dict[tuple, Table] = {}
_TABLE_CACHE_LOCK = threading.Lock()
_TABLE_CACHE_TIMESTAMPS: dict[tuple, float] = {}

def _cache_key(engine: Engine, schema: str | None, table_name: str) -> tuple:
    return (engine.url.render_as_string(hide_password=True), schema, table_name)

def _get_cached_table(key: tuple, ttl: float | None) -> Table | None:
    if key not in _TABLE_CACHE:
        return None
    if ttl is not None:
        import time
        if time.monotonic() - _TABLE_CACHE_TIMESTAMPS[key] > ttl:
            del _TABLE_CACHE[key]
            del _TABLE_CACHE_TIMESTAMPS[key]
            return None
    return _TABLE_CACHE[key]

def _set_cached_table(key: tuple, table: Table) -> None:
    import time
    _TABLE_CACHE[key] = table
    _TABLE_CACHE_TIMESTAMPS[key] = time.monotonic()
```

### 7.3 Thread-safe descriptor

```python
class LazyDBProp:
    def __get__(self, instance, _):
        key = _cache_key(instance.engine, instance.schema, self._name)

        # Fast path: check without lock
        cached = _get_cached_table(key, instance.cache_ttl)
        if cached is not None:
            return cached

        # Slow path: acquire lock and double-check
        with _TABLE_CACHE_LOCK:
            cached = _get_cached_table(key, instance.cache_ttl)
            if cached is not None:
                return cached

            table = self._reflect(instance)
            _set_cached_table(key, table)
            return table
```

### 7.4 Invalidation API

```python
class LazyDB:
    def invalidate(self, table_name: str) -> None:
        """Force re-reflection of a specific table on next access."""
        key = _cache_key(self.engine, self.schema, table_name)
        with _TABLE_CACHE_LOCK:
            _TABLE_CACHE.pop(key, None)
            _TABLE_CACHE_TIMESTAMPS.pop(key, None)
        # Remove from class so descriptor re-triggers
        class_attr = type(self).__dict__.get(table_name)
        if class_attr is not None:
            delattr(type(self), table_name)

    def invalidate_all(self) -> None:
        """Force re-reflection of all tables on next access."""
        prefix = self.engine.url.render_as_string(hide_password=True)
        with _TABLE_CACHE_LOCK:
            stale = [k for k in _TABLE_CACHE if k[0] == prefix]
            for key in stale:
                del _TABLE_CACHE[key]
                _TABLE_CACHE.pop(key, None)

    def preload(self, *table_names: str) -> None:
        """
        Eagerly reflect the given tables. Useful at application startup
        to warm the cache for frequently-accessed tables.
        """
        for name in table_names:
            _ = getattr(self, name)  # triggers __getattr__ → reflection
```

### 7.5 TTL configuration

```python
lazy_db = get_lazy_class(engine, cache_ttl=300)    # re-reflect after 5 minutes
lazy_db = get_lazy_class(engine, cache_ttl=None)   # never expire (default)
lazy_db = get_lazy_class(engine, cache_ttl=0)      # disable cache entirely
```

---

## 8. Phase 5 — Type safety and IDE integration

**Goal:** Make mypy, pyright, and IDE autocomplete work with the library's output.

**Effort:** Low (~1 day)
**Risk:** Very low — purely additive

### 8.1 `py.typed` marker

Create an empty `lazy_alchemy/py.typed` file to declare the package as typed per
PEP 561. This enables mypy and pyright to find the stubs.

### 8.2 `__init__.pyi` stub

```python
# lazy_alchemy/__init__.pyi
from sqlalchemy import Table, Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from typing import overload, Any

class CustomTable(Table):
    def __getattr__(self, attr: str) -> Any: ...
    def __bool__(self) -> bool: ...
    def as_pydantic(self, *, partial: bool = False) -> type: ...
    def as_pydantic_partial(self) -> type: ...
    def as_sqlmodel(self) -> type: ...

class LazyDB:
    engine: Engine
    schema: str | None
    cache_ttl: float | None

    def __getattr__(self, name: str) -> CustomTable: ...
    def invalidate(self, table_name: str) -> None: ...
    def invalidate_all(self) -> None: ...
    def preload(self, *table_names: str) -> None: ...

class AsyncLazyDB:
    engine: AsyncEngine

    async def get(self, table_name: str) -> CustomTable: ...
    def __getattr__(self, name: str) -> CustomTable: ...

@overload
def get_lazy_class(engine: Engine, *, cache_ttl: float | None = None, schema: str | None = None) -> LazyDB: ...
@overload
def get_lazy_class(engine: AsyncEngine, *, cache_ttl: float | None = None, schema: str | None = None) -> AsyncLazyDB: ...
```

### 8.3 Generic typing (optional, advanced)

For power users, a generic version enables precise column type inference:

```python
from typing import TypeVar, Generic, ClassVar

TableT = TypeVar("TableT", bound=CustomTable)

class LazyDB(Generic[TableT]):
    """
    Parametrised version for teams that want strict column typing.
    Most users should use the non-generic `get_lazy_class()` factory.
    """
    ...
```

---

## 9. Phase 6 — Schema-aware features

**Goal:** Add capabilities that leverage reflection data the library already has.

**Effort:** Medium (~3 days)
**Risk:** Low

### 9.1 Multi-schema support

Many production databases use PostgreSQL schema namespacing (e.g. `public`,
`analytics`, `audit`) or multiple MySQL databases.

```python
# One lazy instance per schema
public_db   = get_lazy_class(engine, schema="public")
analytics_db = get_lazy_class(engine, schema="analytics")

users_table = public_db.users
events_table = analytics_db.events
```

Implementation: `schema` is stored on the lazy instance and passed as
`Table(name, metadata, schema=schema, autoload_with=conn)`.

### 9.2 Table listing

```python
lazy_db.list_tables()
# → ['users', 'orders', 'products', 'order_items', ...]

lazy_db.list_tables(pattern="order*")
# → ['orders', 'order_items']
```

### 9.3 Foreign key relationship map

```python
lazy_db.relationships("users")
# → {
#     'orders': FKRelationship(column='user_id', references='users.id'),
#     'sessions': FKRelationship(column='user_id', references='users.id'),
# }
```

### 9.4 `repr` and `info` on `CustomTable`

```python
print(lazy_db.users)
# <CustomTable 'users': id(int, PK), name(str), email(str, unique), created_at(datetime)>

lazy_db.users.info()
# Table: users
# Columns: 4  |  Indexes: 3  |  Foreign keys: 0  |  Size: 12 MB (est.)
```

### 9.5 Reflection context manager

For applications that want to batch-reflect multiple tables in a single connection:

```python
with lazy_db.reflect_context() as ctx:
    users  = ctx.reflect("users")
    orders = ctx.reflect("orders")
    items  = ctx.reflect("order_items")
# All three reflected in a single engine.connect() call
```

---

## 10. Phase 7 — Packaging and tooling modernisation

**Goal:** Bring the project's tooling in line with current Python packaging standards.

**Effort:** Very low (~half a day)
**Risk:** None

### 10.1 Migrate to `pyproject.toml`

Replace `setup.cfg` + `setup.py` + `Pipfile` + `requirements.txt` + `dev_requirements.txt`
with a single `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "lazy-alchemy"
version = "2.0.0"
description = "Lazy-load SQLAlchemy table metadata on demand, with full SA2, async, and Pydantic support."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"
authors = [{ name = "Satyam Soni", email = "satyamsoni@hotmail.co.uk" }]
dependencies = ["sqlalchemy>=1.4"]

[project.optional-dependencies]
async    = ["sqlalchemy[asyncio]>=2.0", "greenlet"]
pydantic = ["pydantic>=2.0"]
sqlmodel = ["sqlmodel>=0.0.14", "pydantic>=2.0"]
dev      = [
    "pytest>=7",
    "pytest-asyncio",
    "pytest-cov",
    "mypy",
    "ruff",
    "sqlalchemy[asyncio]>=2.0",
    "pydantic>=2.0",
    "sqlmodel",
    "aiosqlite",
]

[project.urls]
Homepage    = "https://github.com/satyamsoni2211/lazy_alchemy"
Repository  = "https://github.com/satyamsoni2211/lazy_alchemy"
"Bug Tracker" = "https://github.com/satyamsoni2211/lazy_alchemy/issues"
Changelog   = "https://github.com/satyamsoni2211/lazy_alchemy/releases"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths    = ["tests"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.hatch.version]
path = "lazy_alchemy/__init__.py"
```

### 10.2 Python version support

Update classifiers to declare support for Python 3.10, 3.11, 3.12, and 3.13.
Drop 3.6–3.9 support (they are EOL; SA2 requires 3.8+ and we use `X | Y` union
syntax which requires 3.10).

### 10.3 CI/CD updates

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    strategy:
      matrix:
        python: ["3.10", "3.11", "3.12", "3.13"]
        sqlalchemy: ["1.4", "2.0", "latest"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python }}" }
      - run: pip install "sqlalchemy==${{ matrix.sqlalchemy }}" .[dev]
      - run: pytest --cov=lazy_alchemy --cov-report=xml
      - run: mypy lazy_alchemy
      - run: ruff check lazy_alchemy
```

### 10.4 Test suite expansion

Current tests exist but the coverage requirements for v2 expand significantly:

```
tests/
├── conftest.py              # shared fixtures (sync + async engines, SQLite)
├── test_sync.py             # all sync path tests
├── test_async.py            # all async path tests
├── test_cache.py            # TTL, invalidation, thread-safety, race conditions
├── test_pydantic.py         # as_pydantic(), as_pydantic_partial()
├── test_sqlmodel.py         # as_sqlmodel() — skipped if sqlmodel not installed
├── test_typing.py           # mypy --strict passes on example code
├── test_sa_versions.py      # parametrised: SA 1.4 and SA 2.x paths
└── test_multi_schema.py     # schema= parameter
```

---

## 11. Proposed public API

### v2 public surface

```python
# Factories
from lazy_alchemy import get_lazy_class          # unified (sync + async)

# Sync usage (backwards compatible)
from sqlalchemy import create_engine
engine = create_engine("postgresql://...")
lazy_db = get_lazy_class(engine)
lazy_db = get_lazy_class(engine, cache_ttl=300, schema="analytics")

table = lazy_db.users                            # reflects on first access
table = lazy_db["order_items"]                   # bracket notation (new)
tables = lazy_db.list_tables()                   # list all tables in schema
lazy_db.preload("users", "orders")               # warm cache at startup
lazy_db.invalidate("users")                      # force re-reflect
lazy_db.invalidate_all()                         # wipe entire cache

# Table-level API
table.as_pydantic()                              # → Pydantic BaseModel
table.as_pydantic_partial()                      # → all-Optional BaseModel
table.as_sqlmodel()                              # → SQLModel class (needs [sqlmodel])
table.info()                                     # column/index/fk summary

# Async usage (new in v2)
from sqlalchemy.ext.asyncio import create_async_engine
async_engine = create_async_engine("postgresql+asyncpg://...")
lazy_db = get_lazy_class(async_engine)

users = await lazy_db.get("users")              # awaitable reflection
users = await lazy_db["users"]                  # bracket notation

# Exceptions
from lazy_alchemy import TableNotFoundError, ReflectionError, LazyAlchemyError
```

### Backwards compatibility guarantee

All v1.x code continues to work unchanged with SA 1.4:

```python
# v1.x code — unchanged, still works
from lazy_alchemy import get_lazy_class
from sqlalchemy import create_engine

db_engine = create_engine(DB_CONNECT_STRING)
lazy_db = get_lazy_class(db_engine)
db_model = lazy_db.my_db_table_foo
query = session.query(db_model).filter(db_model.foo == "bar").all()
```

---

## 12. Migration guide (v1 → v2)

### Automatic (no changes needed)

If you are on SQLAlchemy 1.4, your code works without modification.

### SQLAlchemy 2.x upgrade

If you upgrade to SQLAlchemy 2.x, upgrade `lazy_alchemy` to v2 at the same time.
The v2 library handles SA2 automatically — no code changes needed on your side.

### Session API change (recommended, not required)

```python
# Old (still works in SA2 legacy mode)
query = session.query(db_model).filter(db_model.foo == "bar").all()

# New (SA2 native style, recommended)
from sqlalchemy import select
result = session.execute(select(db_model).where(db_model.c.foo == "bar"))
rows = result.all()
```

### Async migration

```python
# Before (sync, blocks event loop in async apps)
engine = create_engine("postgresql://...")
lazy_db = get_lazy_class(engine)
table = lazy_db.users

# After (non-blocking)
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine("postgresql+asyncpg://...")
lazy_db = get_lazy_class(engine)
table = await lazy_db.get("users")
```

---

## 13. Priority and effort matrix

| Phase | Enhancement | Impact | Effort | SA2 required | Breaks v1 compat |
| --- | --- | --- | --- | --- | --- |
| 1 | SA2 `autoload_with` fix | 🔴 Critical | Low (hours) | — | No |
| 1 | SA2 `MetaData` bind removal | 🔴 Critical | Low (hours) | — | No |
| 1 | `TableNotFoundError` guard | 🟠 High | Low | No | No |
| 1 | Custom exception hierarchy | 🟡 Medium | Low | No | No |
| 2 | `AsyncEngine` support | 🟠 High | Medium (3d) | Recommended | No (additive) |
| 2 | `asyncio.Lock` thread safety | 🟠 High | Low | No | No |
| 3 | `as_pydantic()` method | 🟠 High | Medium (3d) | No | No (additive) |
| 3 | `as_sqlmodel()` method | 🟠 High | High (5d) | No | No (optional extra) |
| 4 | Module-level shared cache | 🟡 Medium | Low (1d) | No | No |
| 4 | Cache TTL + invalidation API | 🟡 Medium | Low (1d) | No | No |
| 4 | `preload()` method | 🟡 Medium | Very low | No | No (additive) |
| 5 | `py.typed` + `.pyi` stubs | 🟡 Medium | Low (1d) | No | No |
| 6 | Multi-schema (`schema=` param) | 🟡 Medium | Medium (2d) | Recommended | No (opt-in) |
| 6 | `list_tables()` method | 🟢 Low | Very low | No | No |
| 6 | Relationship map | 🟢 Low | Medium | No | No |
| 7 | `pyproject.toml` migration | 🟡 Medium | Very low (2h) | No | No |
| 7 | Python 3.10–3.13 classifiers | 🟢 Low | Very low (1h) | No | No |
| 7 | CI matrix (SA1.4 + SA2) | 🟡 Medium | Low (2h) | No | No |

### Recommended delivery order

```
Week 1:  Phase 1 (SA2 compat fixes) + Phase 7 (pyproject.toml) → release v1.1.0
Week 2:  Phase 4 (cache overhaul) + Phase 5 (type stubs)       → release v1.2.0
Week 3:  Phase 2 (async support)                                → release v2.0.0-beta
Week 4:  Phase 3 (Pydantic/SQLModel) + Phase 6 (schema extras)  → release v2.0.0
```

---

*Plan authored: May 2026. Covers lazy_alchemy v1.0.3 → v2.0.0.SA1.4 and SA2 compatibility references checked against SQLAlchemy changelog and migration guide.*