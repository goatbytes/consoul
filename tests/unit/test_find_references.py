"""Test find_references tool implementation."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.ai.tools.implementations.find_references import (
    _find_symbol_references,
    find_references,
    get_find_references_config,
    set_find_references_config,
)
from consoul.config.models import FindReferencesToolConfig


class TestConfiguration:
    """Test configuration management."""

    def test_set_get_config(self) -> None:
        """Test setting and getting config."""
        config = FindReferencesToolConfig(max_file_size_kb=2048, max_results=200)
        set_find_references_config(config)

        retrieved = get_find_references_config()

        assert retrieved.max_file_size_kb == 2048
        assert retrieved.max_results == 200

    def test_get_config_default(self) -> None:
        """Test getting default config when not set."""
        # Reset to None
        set_find_references_config(None)  # type: ignore[arg-type]

        config = get_find_references_config()

        assert isinstance(config, FindReferencesToolConfig)
        assert config.max_file_size_kb == 1024  # Default
        assert config.max_results == 100  # Default


class TestFindReferencesTool:
    """Test find_references tool function."""

    def test_find_references_basic(self) -> None:
        """Test basic find_references usage."""
        with patch(
            "consoul.ai.tools.implementations.find_references._find_symbol_references",
        ) as mock_find:
            mock_find.return_value = [
                {
                    "symbol": "foo",
                    "type": "call",
                    "line": 10,
                    "file": "test.py",
                    "text": "foo()",
                    "context_before": [],
                    "context_after": [],
                    "is_definition": False,
                }
            ]

            result = find_references.invoke({"symbol": "foo"})

            import json

            parsed = json.loads(result)
            assert len(parsed) == 1
            assert parsed[0]["symbol"] == "foo"
            assert parsed[0]["type"] == "call"
            assert parsed[0]["is_definition"] is False


class TestSymbolSearch:
    """Test symbol reference search functionality."""

    def test_search_invalid_path(self) -> None:
        """Test search with invalid path raises error."""
        with pytest.raises(ToolExecutionError) as exc_info:
            _find_symbol_references(
                "/nonexistent/path",
                "pattern",
                "project",
                False,
                FindReferencesToolConfig(),
            )

        assert "does not exist" in str(exc_info.value).lower()

    def test_search_invalid_regex(self) -> None:
        """Test search with invalid regex pattern raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ToolExecutionError) as exc_info:
                _find_symbol_references(
                    tmpdir,
                    "[invalid(regex",
                    "project",
                    False,
                    FindReferencesToolConfig(),
                )

            assert "invalid regex" in str(exc_info.value).lower()

    def test_search_invalid_scope(self) -> None:
        """Test search with invalid scope raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ToolExecutionError) as exc_info:
                _find_symbol_references(
                    tmpdir, "foo", "invalid_scope", False, FindReferencesToolConfig()
                )

            assert "invalid scope" in str(exc_info.value).lower()

    def test_search_file_scope_not_a_file(self) -> None:
        """Test file scope with directory path raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ToolExecutionError) as exc_info:
                _find_symbol_references(
                    tmpdir, "foo", "file", False, FindReferencesToolConfig()
                )

            assert "not a file" in str(exc_info.value).lower()

    def test_search_directory_scope_not_a_directory(self) -> None:
        """Test directory scope with file path raises error."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            file_path = Path(f.name)

        try:
            with pytest.raises(ToolExecutionError) as exc_info:
                _find_symbol_references(
                    str(file_path),
                    "foo",
                    "directory",
                    False,
                    FindReferencesToolConfig(),
                )

            assert "not a directory" in str(exc_info.value).lower()
        finally:
            file_path.unlink()
