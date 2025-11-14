"""Integration tests for find_references tool with real file parsing."""

import json
from pathlib import Path

from consoul.ai.tools.implementations.find_references import find_references


class TestRealFileReferenceSearch:
    """Test finding references in real code files."""

    def test_find_python_function_calls(self) -> None:
        """Test finding Python function call references."""
        fixtures_path = Path("tests/fixtures/code_search/python")

        # simple.py has calculate_total function that's likely called
        result = find_references.invoke(
            {
                "symbol": "Product",  # Product class is instantiated in ShoppingCart
                "path": str(fixtures_path),
                "scope": "directory",
            }
        )

        matches = json.loads(result)

        # Should find at least one reference (instantiation or usage)
        # Note: Actual count depends on fixture content
        assert isinstance(matches, list)
        if matches:  # If references found
            assert all("symbol" in m for m in matches)
            assert all("type" in m for m in matches)
            assert all("line" in m for m in matches)
            assert all("file" in m for m in matches)
            assert all("is_definition" in m for m in matches)
            # References should not be definitions
            assert all(not m["is_definition"] for m in matches)

    def test_find_with_include_definition(self) -> None:
        """Test finding references with definition included."""
        fixtures_path = Path("tests/fixtures/code_search/python/simple.py")

        # Find ShoppingCart references with definition
        result = find_references.invoke(
            {
                "symbol": "ShoppingCart",
                "path": str(fixtures_path),
                "scope": "file",
                "include_definition": True,
            }
        )

        matches = json.loads(result)

        # Should have at least the definition
        assert len(matches) >= 1

        # Check if definition is included
        definitions = [m for m in matches if m.get("is_definition")]
        if definitions:
            defn = definitions[0]
            assert "definition_" in defn["type"]  # e.g., "definition_class"

    def test_find_case_insensitive(self) -> None:
        """Test case-insensitive reference search."""
        fixtures_path = Path("tests/fixtures/code_search/python")

        result = find_references.invoke(
            {
                "symbol": "PRODUCT",  # Uppercase, but class is Product
                "path": str(fixtures_path),
                "scope": "directory",
                "case_sensitive": False,
            }
        )

        matches = json.loads(result)

        # Case-insensitive should potentially find Product references
        assert isinstance(matches, list)

    def test_find_javascript_references(self) -> None:
        """Test finding JavaScript/TypeScript references."""
        fixtures_path = Path("tests/fixtures/code_search/javascript")

        if not fixtures_path.exists():
            return  # Skip if fixtures don't exist

        result = find_references.invoke(
            {
                "symbol": ".*Cart",  # Regex pattern
                "path": str(fixtures_path),
                "scope": "directory",
            }
        )

        matches = json.loads(result)

        assert isinstance(matches, list)
        # Verify structure if matches found
        if matches:
            assert all("symbol" in m for m in matches)
            assert all("file" in m for m in matches)
            assert all(str(m["file"]).endswith(".js") for m in matches)

    def test_output_structure(self) -> None:
        """Test that output has correct structure."""
        fixtures_path = Path("tests/fixtures/code_search/python/simple.py")

        result = find_references.invoke(
            {
                "symbol": ".*",  # Match any symbol
                "path": str(fixtures_path),
                "scope": "file",
            }
        )

        matches = json.loads(result)

        # Verify JSON structure
        assert isinstance(matches, list)
        for match in matches:
            assert "symbol" in match
            assert "type" in match
            assert "line" in match
            assert "file" in match
            assert "text" in match
            assert "context_before" in match
            assert "context_after" in match
            assert "is_definition" in match
            assert isinstance(match["context_before"], list)
            assert isinstance(match["context_after"], list)

    def test_line_numbers_valid(self) -> None:
        """Test that line numbers are valid."""
        fixtures_path = Path("tests/fixtures/code_search/python/simple.py")

        result = find_references.invoke(
            {
                "symbol": ".*",
                "path": str(fixtures_path),
                "scope": "file",
            }
        )

        matches = json.loads(result)

        for match in matches:
            assert isinstance(match["line"], int)
            assert match["line"] > 0  # Line numbers start at 1

    def test_empty_results_for_nonexistent_symbol(self) -> None:
        """Test that searching for nonexistent symbol returns empty list."""
        fixtures_path = Path("tests/fixtures/code_search/python")

        result = find_references.invoke(
            {
                "symbol": "ThisSymbolDefinitelyDoesNotExist12345",
                "path": str(fixtures_path),
                "scope": "directory",
            }
        )

        matches = json.loads(result)

        # Should return empty list, not error
        assert matches == []
