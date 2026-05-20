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
# Covers all SQLAlchemy 2.0 sqltypes

def _get_type(name, fallback=None):
    try:
        return getattr(sqlalchemy.types, name)
    except AttributeError:
        return fallback

# Integers
_sa_int = sqlalchemy.types.Integer
_sa_bigint = sqlalchemy.types.BigInteger
_sa_smallint = sqlalchemy.types.SmallInteger
_sa_int_ = _get_type("INT")
_sa_integer_ = _get_type("INTEGER")

# Floats/Numeric
_sa_float = sqlalchemy.types.Float
_sa_numeric = sqlalchemy.types.Numeric
_sa_decimal = _get_type("DECIMAL")
_sa_double = _get_type("Double") or _get_type("DOUBLE")
_sa_real = _get_type("REAL")
_sa_double_precision = _get_type("DOUBLE_PRECISION")

# Strings
_sa_string = sqlalchemy.types.String
_sa_text = sqlalchemy.types.Text
_sa_unicode = sqlalchemy.types.Unicode
_sa_unicodetext = sqlalchemy.types.UnicodeText
_sa_char = _get_type("CHAR")
_sa_varchar = _get_type("VARCHAR")
_sa_nchar = _get_type("NCHAR")
_sa_nvarchar = _get_type("NVARCHAR")
_sa_clob = _get_type("CLOB")

# Booleans
_sa_boolean = sqlalchemy.types.Boolean

# Date/Time
_sa_date = sqlalchemy.types.Date
_sa_datetime = sqlalchemy.types.DateTime
_sa_time = _get_type("Time")
_sa_timestamp = _get_type("TIMESTAMP")
_sa_interval = sqlalchemy.types.Interval

# Binary
_sa_binary = _get_type("BINARY")
_sa_varbinary = _get_type("VARBINARY")
_sa_blob = _get_type("BLOB")
_sa_largebinary = sqlalchemy.types.LargeBinary

# JSON
_sa_json = _get_type("JSON")

# UUID
_uuid_type = _get_type("Uuid") or _get_type("UUID")

# ARRAY
_array_type = _get_type("ARRAY")

# Enum
_sa_enum = sqlalchemy.types.Enum

# Other
_sa_nulltype = sqlalchemy.types.NullType
_sa_typedecorator = sqlalchemy.types.TypeDecorator

SA_TO_PYTHON: dict[type, type] = {
    # Integers
    _sa_int: int,
    _sa_bigint: int,
    _sa_smallint: int,
    # Floats
    _sa_float: float,
    _sa_numeric: decimal.Decimal,
    # Strings
    _sa_string: str,
    _sa_text: str,
    _sa_unicode: str,
    _sa_unicodetext: str,
    # Booleans
    _sa_boolean: bool,
    # Date/Time
    _sa_date: datetime.date,
    _sa_datetime: datetime.datetime,
    _sa_interval: datetime.timedelta,
    # Other
    _sa_nulltype: Any,
    _sa_typedecorator: Any,
}

# Add all version-specific types if they exist
if _sa_int_ is not None:
    SA_TO_PYTHON[_sa_int_] = int
if _sa_integer_ is not None:
    SA_TO_PYTHON[_sa_integer_] = int
if _sa_decimal is not None:
    SA_TO_PYTHON[_sa_decimal] = decimal.Decimal
if _sa_double is not None:
    SA_TO_PYTHON[_sa_double] = float
if _sa_real is not None:
    SA_TO_PYTHON[_sa_real] = float
if _sa_double_precision is not None:
    SA_TO_PYTHON[_sa_double_precision] = float
if _sa_char is not None:
    SA_TO_PYTHON[_sa_char] = str
if _sa_varchar is not None:
    SA_TO_PYTHON[_sa_varchar] = str
if _sa_nchar is not None:
    SA_TO_PYTHON[_sa_nchar] = str
if _sa_nvarchar is not None:
    SA_TO_PYTHON[_sa_nvarchar] = str
if _sa_clob is not None:
    SA_TO_PYTHON[_sa_clob] = str
if _sa_time is not None:
    SA_TO_PYTHON[_sa_time] = datetime.time
if _sa_timestamp is not None:
    SA_TO_PYTHON[_sa_timestamp] = datetime.datetime
if _sa_binary is not None:
    SA_TO_PYTHON[_sa_binary] = bytes
if _sa_varbinary is not None:
    SA_TO_PYTHON[_sa_varbinary] = bytes
if _sa_blob is not None:
    SA_TO_PYTHON[_sa_blob] = bytes
if _sa_largebinary is not None:
    SA_TO_PYTHON[_sa_largebinary] = bytes
if _sa_json is not None:
    SA_TO_PYTHON[_sa_json] = Any
if _uuid_type is not None:
    SA_TO_PYTHON[_uuid_type] = uuid.UUID
if _array_type is not None:
    SA_TO_PYTHON[_array_type] = list
if _sa_enum is not None:
    SA_TO_PYTHON[_sa_enum] = str


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
                    lambda sync_conn: CustomTable(
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