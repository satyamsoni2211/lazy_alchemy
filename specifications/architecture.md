## Architecture

**Purpose**: Lazy-Alchemy is a SQLAlchemy wrapper that loads database model metadata lazily instead of at startup, dramatically improving startup time for projects with many models.

**Core Components**:
- `lazy_alchemy/lazy_alchemy.py` - Main module containing:
  - `CustomTable` - Subclass of SQLAlchemy `Table` with attribute access delegation to `Table.c`
  - `LazyDBProp` - Descriptor that lazily loads table metadata on first access via `autoload=True`
  - `get_lazy_class(engine)` - Factory function that creates a dynamic lazy-loaded class bound to an engine
- `lazy_alchemy/__init__.py` - Exports `get_lazy_class`, `CustomTable`, and `version`

**How Lazy Loading Works**:
1. `get_lazy_class()` creates a dynamically-named class (e.g., `LazyClass_dbname`) with `__getattr__` overridden
2. On first attribute access (e.g., `lazy_class.user`), `__getattr__` creates a `LazyDBProp` descriptor and assigns it as a class attribute
3. Subsequent accesses go directly to the descriptor's `__get__`, which loads the table via `autoload=True` on first call
4. This defers metadata loading until each table is actually referenced

**Version**: `lazy_alchemy/VERSION` (single line file, read via `pathlib.Path.read_text()`)