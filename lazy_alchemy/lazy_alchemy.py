import threading
import time
from typing import Any, Optional

import sqlalchemy
from sqlalchemy import Table, MetaData, inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncEngine
import datetime
import decimal
import uuid

# SA to Python type mapping for Pydantic/SQLModel generation
# Use _get_type for types that may vary across SA 2.x versions

def _get_type(name, fallback=None):
    try:
        return getattr(sqlalchemy.types, name)
    except AttributeError:
        return fallback

_uuid_type = _get_type("Uuid") or _get_type("UUID")
_time_type = _get_type("Time")
_array_type = _get_type("ARRAY")
_json_type = _get_type("JSON")
_jsonb_type = _get_type("JSONB")
_real_type = _get_type("Real")
_binary_type = _get_type("Binary") or _get_type("VARBINARY") or _get_type("BLOB") or _get_type("LargeBinary")
_char_type = _get_type("NCHAR") or _get_type("NVARCHAR") or _get_type("CHAR") or _get_type("VARCHAR")
_bytelength_type = _get_type("ByteLength")

SA_TO_PYTHON: dict[type, type] = {
    # Integers
    sqlalchemy.types.Integer: int,
    sqlalchemy.types.BigInteger: int,
    sqlalchemy.types.SmallInteger: int,
    # Floats
    sqlalchemy.types.Float: float,
    sqlalchemy.types.Numeric: decimal.Decimal,
    # Strings
    sqlalchemy.types.String: str,
    sqlalchemy.types.Text: str,
    sqlalchemy.types.Unicode: str,
    sqlalchemy.types.UnicodeText: str,
    # Booleans
    sqlalchemy.types.Boolean: bool,
    sqlalchemy.types.Enum: str,
    # Date/Time
    sqlalchemy.types.Date: datetime.date,
    sqlalchemy.types.DateTime: datetime.datetime,
    sqlalchemy.types.TIMESTAMP: datetime.datetime,
    sqlalchemy.types.Interval: datetime.timedelta,
    # Other
    sqlalchemy.types.NullType: Any,
    sqlalchemy.types.TypeDecorator: Any,
}

# Add version-specific types if they exist
if _uuid_type is not None:
    SA_TO_PYTHON[_uuid_type] = uuid.UUID
if _time_type is not None:
    SA_TO_PYTHON[_time_type] = datetime.time
if _array_type is not None:
    SA_TO_PYTHON[_array_type] = list
if _real_type is not None:
    SA_TO_PYTHON[_real_type] = float
if _binary_type is not None:
    SA_TO_PYTHON[_binary_type] = bytes
if _char_type is not None:
    SA_TO_PYTHON[_char_type] = str
if _bytelength_type is not None:
    SA_TO_PYTHON[_bytelength_type] = bytes
if _json_type is not None:
    SA_TO_PYTHON[_json_type] = Any
if _jsonb_type is not None:
    SA_TO_PYTHON[_jsonb_type] = Any


def sa_column_to_python_type(column) -> type:
    for sa_type, py_type in SA_TO_PYTHON.items():
        if isinstance(column.type, sa_type):
            return Optional[py_type] if column.nullable else py_type
    return Any


# Module-level shared cache
_TABLE_CACHE: dict[tuple, Table] = {}
_TABLE_CACHE_LOCK = threading.Lock()
_TABLE_CACHE_TIMESTAMPS: dict[tuple, float] = {}


def _cache_key(engine, schema, table_name):
    return (engine.url.render_as_string(hide_password=True), schema, table_name)


def _get_cached_table(key, ttl):
    if key not in _TABLE_CACHE:
        return None
    if ttl is not None:
        if time.monotonic() - _TABLE_CACHE_TIMESTAMPS[key] > ttl:
            del _TABLE_CACHE[key]
            del _TABLE_CACHE_TIMESTAMPS[key]
            return None
    return _TABLE_CACHE[key]


def _set_cached_table(key, table):
    _TABLE_CACHE[key] = table
    _TABLE_CACHE_TIMESTAMPS[key] = time.monotonic()


class LazyAlchemyError(Exception):
    """Base exception for lazy_alchemy."""


class TableNotFoundError(LazyAlchemyError):
    """Raised when a requested table does not exist in the schema."""


class ReflectionError(LazyAlchemyError):
    """Raised when table metadata cannot be reflected."""


class CustomTable(Table):
    def __getattr__(self, attr):
        return getattr(self.c, attr)

    def __bool__(self) -> bool:
        return self is not None

    def as_pydantic(self, *, partial: bool = False):
        """
        Generate a Pydantic v2 model from this table's reflected schema.

        Args:
            partial: If True, all fields are Optional (useful for PATCH endpoints).

        Returns:
            A dynamically created Pydantic BaseModel subclass.
        """
        from pydantic import create_model

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

    def as_pydantic_partial(self):
        """All fields Optional. Use for PATCH/UPDATE endpoints."""
        return self.as_pydantic(partial=True)

    def as_sqlmodel(self):
        """
        Generate a SQLModel class from reflected schema.
        """
        from sqlmodel import SQLModel, Field

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
            (SQLModel,),
            namespace,
        )


class LazyDBProp(object):
    """This descriptor returns sqlalchemy Table class which can be used to query table from the schema."""

    def __init__(self) -> None:
        self._table = None
        self._name = None

    def __set_name__(self, _, name):
        self._name = name

    def __set__(self, instance, value):
        if isinstance(value, (CustomTable, Table)):
            self._table = value

    def _reflect(self, instance):
        """Perform the actual table reflection."""
        inspector = sa_inspect(instance.engine)
        available = inspector.get_table_names(schema=instance.schema)
        if self._name not in available:
            raise TableNotFoundError(
                f"Table '{self._name}' not found in database "
                f"'{instance.engine.url.database}'. "
                f"Available tables: {', '.join(sorted(available))}"
            )

        with instance.engine.connect() as conn:
            return CustomTable(
                self._name,
                instance.metadata,
                schema=instance.schema,
                autoload_with=conn,
            )

    def __get__(self, instance, _):
        if self._table is None:
            key = _cache_key(instance.engine, instance.schema, self._name)
            cached = _get_cached_table(key, instance.cache_ttl)
            if cached is not None:
                self._table = cached
                return cached

            with _TABLE_CACHE_LOCK:
                cached = _get_cached_table(key, instance.cache_ttl)
                if cached is not None:
                    self._table = cached
                    return cached

                table = self._reflect(instance)
                _set_cached_table(key, table)
                self._table = table
                return table

        return self._table


def get_sync_lazy_class(engine, *, cache_ttl=None, schema=None):
    """
    Create a sync lazy class for pulling table objects using SQLAlchemy metadata.
    """

    def __init__(self, engine):
        self.metadata = MetaData()
        self.engine = engine
        self.schema = schema
        self.cache_ttl = cache_ttl

    def __getattr__(self, attr):
        if attr not in self.__dict__:
            obj = self.__patch(attr)
        return obj.__get__(self, type(self))

    def __patch(self, attribute):
        obj = LazyDBProp()
        obj.__set_name__(self, attribute)
        setattr(type(self), attribute, obj)
        return obj

    def invalidate(self, table_name):
        """Force re-reflection of a specific table on next access."""
        key = _cache_key(self.engine, self.schema, table_name)
        with _TABLE_CACHE_LOCK:
            _TABLE_CACHE.pop(key, None)
            _TABLE_CACHE_TIMESTAMPS.pop(key, None)

    def invalidate_all(self):
        """Force re-reflection of all tables on next access."""
        prefix = self.engine.url.render_as_string(hide_password=True)
        with _TABLE_CACHE_LOCK:
            stale = [k for k in _TABLE_CACHE if k[0] == prefix]
            for key in stale:
                del _TABLE_CACHE[key]
                _TABLE_CACHE_TIMESTAMPS.pop(key, None)

    def preload(self, *table_names):
        """Eagerly reflect the given tables."""
        for name in table_names:
            getattr(self, name)

    def list_tables(self):
        """List all tables in the schema."""
        inspector = sa_inspect(self.engine)
        return inspector.get_table_names(schema=self.schema)

    # naming classes uniquely for different schema's to avoid cross referencing
    LazyClass = type(f"LazyClass_{engine.url.database}", (), {})
    LazyClass.__init__ = __init__
    LazyClass.__getattr__ = __getattr__
    LazyClass.__patch = __patch
    LazyClass.invalidate = invalidate
    LazyClass.invalidate_all = invalidate_all
    LazyClass.preload = preload
    LazyClass.list_tables = list_tables
    return LazyClass(engine)


class AsyncLazyDBAccessor:
    """Awaitable table accessor for async contexts."""

    def __init__(self, engine: AsyncEngine, metadata: MetaData, schema=None, cache_ttl=None):
        self._engine = engine
        self._metadata = metadata
        self._schema = schema
        self._cache_ttl = cache_ttl
        self._cache: dict[str, Table] = {}
        self._lock = None  # asyncio.Lock() must be created in async context

    async def get(self, table_name: str) -> Table:
        import asyncio
        if table_name in self._cache:
            return self._cache[table_name]

        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            if table_name in self._cache:
                return self._cache[table_name]

            async with self._engine.connect() as conn:
                table = await conn.run_sync(
                    lambda sync_conn: Table(
                        table_name,
                        self._metadata,
                        schema=self._schema,
                        autoload_with=sync_conn,
                    )
                )
            self._cache[table_name] = table
            return table

    async def invalidate(self, table_name: str):
        """Force re-reflection of a specific table."""
        self._cache.pop(table_name, None)

    async def invalidate_all(self):
        """Clear entire cache."""
        self._cache.clear()


def get_async_lazy_class(engine: AsyncEngine, *, cache_ttl=None, schema=None):
    """Create an async lazy class for async engine contexts."""
    metadata = MetaData()
    return AsyncLazyDBAccessor(engine, metadata, schema=schema, cache_ttl=cache_ttl)


def get_lazy_class(engine, *, cache_ttl=None, schema=None):
    """
    Unified factory. Returns the appropriate lazy class based on engine type.

    - Sync Engine → LazyDB (attribute access, backwards compatible)
    - AsyncEngine → AsyncLazyDBAccessor (awaitable .get() accessor)
    """
    if isinstance(engine, AsyncEngine):
        return get_async_lazy_class(engine, cache_ttl=cache_ttl, schema=schema)
    return get_sync_lazy_class(engine, cache_ttl=cache_ttl, schema=schema)