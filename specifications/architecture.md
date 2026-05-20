## Architecture

**Purpose**: Lazy-Alchemy is a SQLAlchemy wrapper that loads database model metadata lazily instead of at startup, dramatically improving startup time for projects with many models.

**Core Components**:

- `lazy_alchemy/lazy_alchemy.py` - Main module containing:
  - `CustomTable` - Subclass of SQLAlchemy `Table` with attribute access delegation to `Table.c`, plus `as_pydantic()`, `as_pydantic_partial()`, and `as_sqlmodel()` methods
  - `LazyDBProp` - Descriptor that lazily loads table metadata on first access via `autoload_with=conn`
  - `get_lazy_class(engine)` - Factory function that creates either a sync `LazyDB` or async `AsyncLazyDBAccessor` depending on engine type
  - `AsyncLazyDBAccessor` - Awaitable table accessor for async engines with `asyncio.Lock` double-checked locking
- `lazy_alchemy/__init__.py` - Exports `get_lazy_class`, `CustomTable`, and `version`

**How Lazy Loading Works**:

1. `get_lazy_class()` creates a dynamically-named class (e.g., `LazyClass_dbname`) with `__getattr__` overridden, or an `AsyncLazyDBAccessor` for async engines
2. On first attribute access (e.g., `lazy_class.user`), `__getattr__` creates a `LazyDBProp` descriptor and assigns it as a class attribute
3. Subsequent accesses go directly to the descriptor's `__get__`, which loads the table via `autoload_with=conn` on first call
4. This defers metadata loading until each table is actually referenced
5. For async engines, `lazy_db.get("table_name")` returns an awaitable that uses `asyncio.Lock` for double-checked locking before reflection

**Version**: `lazy_alchemy/VERSION` (single line file, read via `pathlib.Path.read_text()`)