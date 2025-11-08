# Development Environment Setup

This guide will help you set up your development environment for contributing to Consoul.

## Prerequisites

- Python 3.10 or higher
- [Poetry](https://python-poetry.org/) for dependency management
- Git for version control

## Environment Setup

### 1. Install Python

We recommend using [pyenv](https://github.com/pyenv/pyenv) to manage Python versions:

```bash
# Install pyenv (macOS)
brew install pyenv

# Install Python 3.12 (or your preferred version >= 3.10)
pyenv install 3.12.3
pyenv local 3.12.3
```

Alternatively, you can use your system Python if it's version 3.10 or higher.

### 2. Install Poetry

```bash
# macOS/Linux/WSL
curl -sSL https://install.python-poetry.org | python3 -

# Or via pip
pip install poetry
```

### 3. Clone the Repository

```bash
git clone https://github.com/goatbytes/consoul.git
cd consoul
```

### 4. Install Dependencies

```bash
# Install all dependencies including dev, docs, and security tools
make install-dev

# Or using Poetry directly
poetry install --with dev,docs,security
```

## Development Workflow

### Running Tests

```bash
# Run tests with coverage report
make test

# Run tests without coverage (faster)
make test-fast

# Or using Poetry directly
poetry run pytest -v --cov
```

### Code Quality Checks

```bash
# Run linting checks
make lint

# Auto-fix linting issues
make lint-fix

# Format code
make format

# Check code formatting without changes
make format-check

# Run type checking
make type-check

# Run all quality checks (lint + format-check + type-check)
make quality
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality before commits:

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run pre-commit on all files
make pre-commit

# Pre-commit will automatically run on git commit
```

The pre-commit hooks include:
- Trailing whitespace removal
- End-of-file fixer
- YAML/TOML/JSON validation
- Ruff linting and formatting
- Mypy type checking

### Building the Package

```bash
# Build distribution packages
make build

# This creates wheel and source distributions in dist/
```

### Building Documentation

```bash
# Build documentation (when configured)
make docs
```

*Note: Documentation build is not yet fully configured.*

### Updating Dependencies

```bash
# Update all dependencies to latest compatible versions
make update

# Or using Poetry directly
poetry update
```

### Cleaning Build Artifacts

```bash
# Remove build artifacts, caches, and temporary files
make clean
```

## Project Structure

```
consoul/
├── src/consoul/          # Main package source code
│   ├── __init__.py       # Package metadata
│   ├── __main__.py       # CLI entry point
│   ├── ai/               # AI integration modules
│   ├── tui/              # Textual TUI components
│   ├── config/           # Configuration management
│   └── utils/            # Utility functions
├── tests/                # Test suite
│   ├── conftest.py       # Pytest fixtures
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── docs/                 # Documentation
├── .github/              # GitHub Actions workflows
├── pyproject.toml        # Project configuration
├── poetry.lock           # Locked dependencies
├── Makefile              # Development task automation
└── README.md             # Project README
```

## Troubleshooting

### Poetry Installation Issues

If you encounter issues installing Poetry:

1. Ensure Python 3.10+ is installed and available
2. Try the alternative installation method (pip vs official installer)
3. Check that `~/.local/bin` or equivalent is in your PATH

### Dependency Resolution Errors

If Poetry fails to resolve dependencies:

```bash
# Clear Poetry cache
poetry cache clear pypi --all

# Try installing again
poetry install --with dev,docs,security
```

### Pre-commit Hook Failures

If pre-commit hooks fail:

1. Read the error message carefully
2. Run the specific tool manually (e.g., `make lint-fix`, `make format`)
3. Stage the auto-fixed changes and commit again

### Type Checking Errors

If mypy reports errors:

1. Ensure all dependencies are installed: `make install-dev`
2. Check that `py.typed` marker exists in `src/consoul/`
3. Review mypy configuration in `pyproject.toml`

### Test Failures

If tests fail:

1. Ensure all dev dependencies are installed
2. Check that you're using Python 3.10+
3. Run with verbose output: `poetry run pytest -vv`
4. Check for missing test fixtures in `conftest.py`

## Getting Help

- **Documentation**: See the [documentation home](index.md)
- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/goatbytes/consoul/issues)
- **Contributing**: Review [CONTRIBUTING.md](contributing.md) for guidelines

## Code Style Guidelines

### Python Style

- **Line Length**: 88 characters (Ruff default)
- **Indentation**: 4 spaces
- **Imports**: Sorted and grouped (isort compatible)
- **Type Hints**: Required for all public APIs
- **Docstrings**: Google style for all public modules, classes, and functions

### Commit Messages

Follow conventional commits format:

```
type(scope): brief description

Longer description if needed.

Gira: SOUL-XXX
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`

### Branch Naming

- Feature: `feature/SOUL-XXX-description`
- Bug fix: `fix/SOUL-XXX-description`
- Docs: `docs/SOUL-XXX-description`

## IDE Setup

### VS Code (Recommended)

The project includes workspace settings in `.vscode/settings.json` with:

- Python path configuration
- Ruff extension integration
- Mypy extension integration
- Test discovery configuration

Install recommended extensions:
- Python (ms-python.python)
- Ruff (charliermarsh.ruff)
- Mypy Type Checker (ms-python.mypy-type-checker)

### PyCharm

1. Open project directory
2. PyCharm should auto-detect Poetry and configure the interpreter
3. Enable Poetry in: Settings → Project → Python Interpreter → Poetry Environment
4. Configure Ruff and mypy in external tools if desired

## Next Steps

After setting up your environment:

1. Run `make quality` to verify everything works
2. Run `make test` to ensure all tests pass
3. Review [CONTRIBUTING.md](contributing.md) for contribution guidelines
4. Check open issues on GitHub for tasks to work on
5. Sign the [Contributor License Agreement](https://forms.gle/J5iqyH4hrHQQDfUCA)

Happy coding! 🚀
