# Lazy-Alchemy

*Lazy-Alchemy* is a Python package that loads database models lazily. It's a wrapper on top of SQLAlchemy, so Lazy-Alchemy can be used with any framework or project that uses SQLAlchemy.

SQLAlchemy loads the entire metadata of all models during application startup, which can significantly increase start-up time. In projects with 100s of database models, startup time can be in minutes due to loading model metadata.

Lazy-Alchemy solves this by only loading models "on-demand", boosting startup time from minutes to seconds and saving memory.

[![Pypi tag](https://img.shields.io/pypi/v/lazy_alchemy.svg?style=flat-square&label=version)](https://pypi.org/project/lazy_alchemy/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/lazy_alchemy)
![Licence](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)

---

## Compatibility

- Python >= 3.10
- SQLAlchemy 1.4 / 2.x

## Installation

```bash
pip install lazy-alchemy            # Includes async, Pydantic v2, SQLModel
pip install lazy-alchemy[dev]       # Dev dependencies + tests
```

## Basic Usage

```python
from lazy_alchemy import get_lazy_class
from sqlalchemy import create_engine

db_engine = create_engine(DB_CONNECT_STRING)
lazy_db = get_lazy_class(db_engine)

# Access table on first use (lazy reflection)
db_model = lazy_db.my_table
```

### Async Usage

```python
from sqlalchemy.ext.asyncio import create_async_engine
from lazy_alchemy import get_lazy_class

async_engine = create_async_engine(DB_CONNECT_STRING)
lazy_db = get_lazy_class(async_engine)

# In async context:
users_table = await lazy_db.get("users")
```

### Pydantic v2 Models

```python
lazy_db = get_lazy_class(engine)

# Generate Pydantic model from reflected table
UserSchema = lazy_db.users.as_pydantic()
user = UserSchema(username="alice", age=30)

# For PATCH endpoints (all fields Optional)
UserPatch = lazy_db.users.as_pydantic_partial()
```

### SQLModel Integration

```python
lazy_db = get_lazy_class(engine)

# Generate SQLModel class
User = lazy_db.users.as_sqlmodel()

# Use with FastAPI
@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, session: Session = Depends(get_session)):
    return session.get(User, user_id)
```

### Cache Management

```python
lazy_db = get_lazy_class(engine, cache_ttl=300)  # 5 min TTL

# Preload tables at startup
lazy_db.preload("users", "orders")

# Invalidate specific table
lazy_db.invalidate("users")

# Clear all cached tables
lazy_db.invalidate_all()

# List available tables
tables = lazy_db.list_tables()
```

### Exceptions

```python
from lazy_alchemy import TableNotFoundError, LazyAlchemyError

try:
    table = lazy_db.nonexistent_table
except TableNotFoundError as e:
    print(e)  # Helpful message with available tables
```

## Tests

```bash
pytest
```

---

## License

Lazy-Alchemy is released under the MIT License. See the bundled `LICENSE` file for details.