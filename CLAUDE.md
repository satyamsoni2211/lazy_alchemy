# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Refer below documents for specific requirements:

- Building and Testing: refer @specifications/build_and_test.md
- Architecture: refer @specifications/architecture.md

## v2.0 Changes

lazy_alchemy v2.0 brings SQLAlchemy 2.x compatibility, async support, Pydantic v2/SQLModel integration, and production-grade caching.

### Key Changes

**SQLAlchemy 2.x Compatibility:**
- Uses `autoload_with=conn` instead of deprecated `autoload=True`
- Uses `MetaData()` without bind parameter
- Custom exception hierarchy: `LazyAlchemyError`, `TableNotFoundError`, `ReflectionError`

**Async Support:**
- `get_lazy_class(async_engine)` returns `AsyncLazyDBAccessor`
- Use `await lazy_db.get("table_name")` for async reflection

**Pydantic/SQLModel:**
- `table.as_pydantic()` → Pydantic BaseModel
- `table.as_pydantic_partial()` → all-Optional BaseModel
- `table.as_sqlmodel()` → SQLModel class

**Cache Architecture:**
- Module-level thread-safe cache with TTL support
- `invalidate()`, `invalidate_all()`, `preload()` methods
- `cache_ttl` parameter on `get_lazy_class()`

**Type Safety:**
- `py.typed` marker for PEP 561
- `__init__.pyi` type stubs

### Installation

```bash
pip install lazy-alchemy          # base
pip install lazy-alchemy[async]    # async support
pip install lazy-alchemy[pydantic] # Pydantic v2
pip install lazy-alchemy[sqlmodel] # SQLModel
pip install lazy-alchemy[dev]      # all extras
```