# Publishing Consoul to PyPI

This document describes how to publish new versions of Consoul to PyPI.

## Prerequisites

- PyPI account at https://pypi.org
- PyPI API token configured in Poetry

## One-Time Setup

### 1. Create PyPI API Token

1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Name: `consoul-publish`
4. Scope: "Project: consoul" (or "Entire account")
5. Copy the token (starts with `pypi-`)

### 2. Configure Poetry

```bash
poetry config pypi-token.pypi YOUR_TOKEN_HERE
```

Or use environment variable:

```bash
export PYPI_TOKEN=your-token-here
poetry config pypi-token.pypi $PYPI_TOKEN
```

## Publishing a New Version

### 1. Update Version

Edit `pyproject.toml` and update the version number in both locations:

```toml
[project]
version = "0.1.1"

[tool.poetry]
version = "0.1.1"
```

### 2. Update CHANGELOG.md

Document changes in `CHANGELOG.md` following the existing format.

### 3. Commit Version Bump

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.1.1"
git tag v0.1.1
```

### 4. Build Package

```bash
poetry build
```

This creates:
- `dist/consoul-X.Y.Z.tar.gz` (source distribution)
- `dist/consoul-X.Y.Z-py3-none-any.whl` (wheel)

### 5. Publish to PyPI

```bash
poetry publish
```

### 6. Push to GitHub

```bash
git push origin develop
git push origin v0.1.1
```

## Verify Publication

Check the package page: https://pypi.org/project/consoul/

Test installation:

```bash
pip install --upgrade consoul
```

## Installation Options

Users can install Consoul with different feature sets:

```bash
# SDK only (core dependencies)
pip install consoul

# With TUI
pip install consoul[tui]

# With specific features
pip install consoul[ollama-library]
pip install consoul[pdf]

# All features
pip install consoul[all]
```

## Troubleshooting

### Authentication Failed

Re-configure your PyPI token:

```bash
poetry config pypi-token.pypi YOUR_NEW_TOKEN
```

### Version Already Exists

You cannot republish the same version. Bump the version number and try again.

### Build Errors

Ensure your environment is clean:

```bash
rm -rf dist/
poetry build
```

## TestPyPI (Optional)

To test publishing without affecting the production PyPI:

```bash
# Configure TestPyPI token
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi YOUR_TEST_TOKEN

# Publish to TestPyPI
poetry publish -r testpypi

# Test installation
pip install --index-url https://test.pypi.org/simple/ consoul
```
