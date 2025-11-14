"""Integration tests for code_search tool with real files."""

import json
from pathlib import Path

from consoul.ai.tools.implementations.code_search import code_search


class TestRealFileSearch:
    """Test search with real fixture files."""

    def test_search_python_functions(self) -> None:
        """Test searching for Python functions."""
        fixtures_path = Path("tests/fixtures/code_search/python")

        result = code_search.invoke(
            {
                "query": "calculate_total",
                "path": str(fixtures_path),
                "symbol_type": "function",
            }
        )

        matches = json.loads(result)

        # Should find calculate_total function in simple.py
        assert len(matches) >= 1
        assert any(m["name"] == "calculate_total" for m in matches)
        assert all(m["type"] == "function" for m in matches)

    def test_search_python_classes(self) -> None:
        """Test searching for Python classes."""
        fixtures_path = Path("tests/fixtures/code_search/python")

        result = code_search.invoke(
            {
                "query": "Shopping.*",
                "path": str(fixtures_path),
                "symbol_type": "class",
            }
        )

        matches = json.loads(result)

        # Should find ShoppingCart class
        assert len(matches) >= 1
        shopping_cart = next((m for m in matches if m["name"] == "ShoppingCart"), None)
        assert shopping_cart is not None
        assert shopping_cart["type"] == "class"

    def test_search_case_insensitive(self) -> None:
        """Test case-insensitive search."""
        fixtures_path = Path("tests/fixtures/code_search/python")

        result = code_search.invoke(
            {
                "query": "CALCULATE",
                "path": str(fixtures_path),
                "case_sensitive": False,
            }
        )

        matches = json.loads(result)

        # Should find calculate_total (case-insensitive)
        assert len(matches) >= 1
        assert any("calculate" in m["name"].lower() for m in matches)

    def test_search_javascript_classes(self) -> None:
        """Test searching JavaScript classes."""
        fixtures_path = Path("tests/fixtures/code_search/javascript")

        result = code_search.invoke(
            {
                "query": ".*Cart",
                "path": str(fixtures_path),
                "symbol_type": "class",
            }
        )

        matches = json.loads(result)

        # Should find ShoppingCart class in simple.js
        assert len(matches) >= 1
        cart = next((m for m in matches if "Cart" in m["name"]), None)
        assert cart is not None

    def test_search_go_functions(self) -> None:
        """Test searching Go functions."""
        fixtures_path = Path("tests/fixtures/code_search/go")

        result = code_search.invoke(
            {
                "query": "Calculate.*",
                "path": str(fixtures_path),
                "symbol_type": "function",
            }
        )

        matches = json.loads(result)

        # Should find CalculateTotal function
        assert len(matches) >= 1
        calc = next((m for m in matches if "Calculate" in m["name"]), None)
        assert calc is not None

    def test_search_multi_language(self) -> None:
        """Test searching across multiple languages."""
        fixtures_path = Path("tests/fixtures/code_search")

        result = code_search.invoke(
            {
                "query": ".*Total.*",
                "path": str(fixtures_path),
            }
        )

        matches = json.loads(result)

        # Should find symbols from Python, JavaScript, and Go
        files = {m["file"] for m in matches}
        assert any(".py" in f for f in files)
        assert any(".js" in f for f in files)
        assert any(".go" in f for f in files)

    def test_output_structure(self) -> None:
        """Test output has required structure."""
        fixtures_path = Path("tests/fixtures/code_search/python")

        result = code_search.invoke(
            {
                "query": "calculate_total",
                "path": str(fixtures_path),
            }
        )

        matches = json.loads(result)

        for match in matches:
            # Required fields
            assert "name" in match
            assert "type" in match
            assert "line" in match
            assert "file" in match
            assert "text" in match
            assert "context_before" in match
            assert "context_after" in match

            # Type checks
            assert isinstance(match["name"], str)
            assert isinstance(match["type"], str)
            assert isinstance(match["line"], int)
            assert isinstance(match["file"], str)
            assert isinstance(match["text"], str)
            assert isinstance(match["context_before"], list)
            assert isinstance(match["context_after"], list)

    def test_line_numbers_valid(self) -> None:
        """Test line numbers are positive."""
        fixtures_path = Path("tests/fixtures/code_search/python")

        result = code_search.invoke(
            {
                "query": ".*",
                "path": str(fixtures_path),
            }
        )

        matches = json.loads(result)

        for match in matches:
            assert match["line"] > 0
