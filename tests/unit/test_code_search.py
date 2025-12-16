"""Test code_search tool implementation."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.ai.tools.implementations.code_search import (
    _is_supported_file,
    _search_symbols,
    code_search,
    get_code_search_config,
    set_code_search_config,
)
from consoul.config.models import CodeSearchToolConfig


class TestConfiguration:
    """Test configuration management."""

    def test_set_get_config(self) -> None:
        """Test setting and getting config."""
        config = CodeSearchToolConfig(max_file_size_kb=2048)
        set_code_search_config(config)

        retrieved = get_code_search_config()

        assert retrieved.max_file_size_kb == 2048

    def test_get_config_default(self) -> None:
        """Test getting default config when not set."""
        # Reset to None
        set_code_search_config(None)  # type: ignore[arg-type]

        config = get_code_search_config()

        assert isinstance(config, CodeSearchToolConfig)
        assert config.max_file_size_kb == 1024  # Default


class TestFileSupportCheck:
    """Test file support checking."""

    def test_supported_extension(self) -> None:
        """Test file with supported extension."""
        config = CodeSearchToolConfig()
        test_file = Path("test.py")

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            test_file = Path(f.name)
            try:
                assert _is_supported_file(test_file, config) is True
            finally:
                test_file.unlink()

    def test_unsupported_extension(self) -> None:
        """Test file with unsupported extension."""
        config = CodeSearchToolConfig()
        test_file = Path("test.txt")

        assert _is_supported_file(test_file, config) is False

    def test_file_too_large(self) -> None:
        """Test file exceeding size limit."""
        config = CodeSearchToolConfig(max_file_size_kb=1)

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            # Write 2KB of data
            f.write(b"x" * 2048)
            f.flush()  # Ensure data is written to disk
            test_file = Path(f.name)

        try:
            assert _is_supported_file(test_file, config) is False
        finally:
            test_file.unlink()


class TestCodeSearchTool:
    """Test code_search tool function."""

    def test_code_search_basic(self) -> None:
        """Test basic code_search usage."""
        with (
            patch(
                "consoul.ai.tools.implementations.code_search._search_symbols",
            ) as mock_search,
        ):
            mock_search.return_value = [
                {
                    "name": "test_func",
                    "type": "function",
                    "line": 1,
                    "file": "test.py",
                    "text": "def test_func():",
                    "context_before": [],
                    "context_after": [],
                    "parent": None,
                }
            ]

            result = code_search.invoke({"query": "test_func"})

            import json

            parsed = json.loads(result)
            assert len(parsed) == 1
            assert parsed[0]["name"] == "test_func"


class TestSearchSymbols:
    """Test symbol search functionality."""

    def test_search_invalid_path(self) -> None:
        """Test search with invalid path raises error."""
        with pytest.raises(ToolExecutionError) as exc_info:
            _search_symbols("/nonexistent/path", "pattern")

        assert "does not exist" in str(exc_info.value).lower()

    def test_search_invalid_regex(self) -> None:
        """Test search with invalid regex pattern raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ToolExecutionError) as exc_info:
                _search_symbols(tmpdir, "[invalid(regex")

            assert "invalid regex" in str(exc_info.value).lower()
