## Build & Test Commands

```bash
# Run tests
pytest

# Run tests with coverage
coverage run -m pytest && coverage html && open htmlcov/index.html

# Build distribution (runs tests first via Makefile)
make build

# Install dev dependencies
make install

# Clean build artifacts
make clean
```
