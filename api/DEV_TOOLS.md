# Development Tools Guide

This project uses modern Python development tools for better code quality and faster development.

## Tools Overview

### Package Management: uv
[uv](https://github.com/astral-sh/uv) is a blazing-fast Python package installer (10-100x faster than pip).

**Installation:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

**Usage:**
```bash
# Install dependencies
make install         # Production only
make install-dev     # With dev tools

# Or directly with uv
uv pip install -r requirements.txt
```

### Code Formatting: Black & isort

**Black** - Uncompromising Python code formatter
- Line length: 100
- Target: Python 3.11
- Config: `pyproject.toml`

**isort** - Import statement organizer
- Profile: black (compatible with Black)
- Config: `pyproject.toml`

**Usage:**
```bash
# Format code
make format

# Check formatting (CI)
make format-check

# Or directly
black .
isort .
```

### Linting: Flake8

**Flake8** - Style guide enforcement
- Max line length: 100
- Config: `.flake8`

**Usage:**
```bash
make lint

# Or directly
flake8 .
```

### Pre-commit Hooks

Automatically format and lint code before commits.

**Setup:**
```bash
make pre-commit-install

# Run manually
make pre-commit-run
```

**Hooks:**
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON/TOML validation
- Black formatting
- isort import sorting
- Flake8 linting

## Python 3.11 Features

This project targets Python 3.11 and uses modern syntax:

### Type Hints
```python
# Old style (Python 3.9)
from typing import Optional, Dict, List
def func(x: Optional[str]) -> Dict[str, List[int]]:
    ...

# New style (Python 3.11) - preferred
def func(x: str | None) -> dict[str, list[int]]:
    ...
```

### Exception Groups (PEP 654)
```python
try:
    ...
except* ValueError as e:
    # Handle multiple ValueError instances
    pass
```

### Performance
- 10-60% faster than Python 3.10
- Better memory usage
- Faster async/await operations

## Makefile Commands

```bash
# Installation
make install          # Install production dependencies
make install-dev      # Install with dev tools

# Development
make run             # Start API server
make run-worker      # Start worker

# Testing
make test            # Run unit tests
make test-integration # Run integration tests (P1 only)
make test-all        # Run all tests with coverage

# Code Quality
make format          # Format code
make format-check    # Check formatting
make lint            # Run linters
make pre-commit-run  # Run all pre-commit hooks

# Docker
make docker-build    # Build images
make docker-up       # Start services
make docker-down     # Stop services
make docker-logs     # View logs

# Database
make migrate         # Run migrations
make migrate-create  # Create new migration
make migrate-down    # Rollback one migration

# Cleanup
make clean           # Remove build artifacts
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Install uv
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Install dependencies
  run: uv pip install -r requirements.txt -r requirements-dev.txt

- name: Check formatting
  run: |
    black --check .
    isort --check .

- name: Lint
  run: flake8 .

- name: Test
  run: pytest tests/ -v
```

### Pre-commit in CI
```yaml
- name: Run pre-commit
  run: |
    pip install pre-commit
    pre-commit run --all-files
```

## Configuration Files

- **pyproject.toml** - Black, isort, pytest config
- **.flake8** - Flake8 linting rules
- **.pre-commit-config.yaml** - Pre-commit hook definitions
- **Makefile** - Common development commands
- **requirements.txt** - Production dependencies
- **requirements-dev.txt** - Development dependencies
- **requirements-test.txt** - Testing dependencies

## Best Practices

1. **Always format before committing:**
   ```bash
   make format
   ```

2. **Install pre-commit hooks:**
   ```bash
   make pre-commit-install
   ```

3. **Use uv for faster installs:**
   ```bash
   uv pip install package_name
   ```

4. **Run tests before pushing:**
   ```bash
   make test
   ```

5. **Check code quality:**
   ```bash
   make format-check
   make lint
   ```

## Troubleshooting

### uv not found
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or fallback to pip (slower)
pip install -r requirements.txt
```

### Black formatting conflicts
```bash
# Re-run black
black .

# Check what would change
black --diff .
```

### Pre-commit hook failures
```bash
# Run hooks manually
pre-commit run --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

## Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Python 3.11 What's New](https://docs.python.org/3/whatsnew/3.11.html)
