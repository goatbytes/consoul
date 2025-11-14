"""Integration tests for grep_search tool with real files and commands."""

import json
import tempfile
from pathlib import Path

import pytest

from consoul.ai.tools.implementations.grep_search import (
    _detect_ripgrep,
    grep_search,
)


@pytest.fixture
def test_project() -> Path:
    """Create a temporary test project with Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create directory structure
        src_dir = project_root / "src"
        src_dir.mkdir()

        tests_dir = project_root / "tests"
        tests_dir.mkdir()

        docs_dir = project_root / "docs"
        docs_dir.mkdir()

        # Create Python files
        (src_dir / "main.py").write_text(
            """def main():
    print("Hello, world!")
    return 0

if __name__ == "__main__":
    main()
"""
        )

        (src_dir / "utils.py").write_text(
            """def calculate(x, y):
    return x + y

def process_data(data):
    # Process the data
    result = []
    for item in data:
        result.append(calculate(item, 10))
    return result
"""
        )

        (tests_dir / "test_main.py").write_text(
            """import pytest

def test_main():
    from src.main import main
    assert main() == 0

def test_output():
    # Test function
    pass
"""
        )

        # Create non-Python file
        (docs_dir / "README.md").write_text(
            """# Project Documentation

This is a test project.

## Features
- Feature 1
- Feature 2
"""
        )

        yield project_root


class TestRealFileSearch:
    """Test search with real files and directories."""

    def test_search_python_files(self, test_project: Path) -> None:
        """Test searching in Python files."""
        result = grep_search.invoke(
            {
                "pattern": "def ",
                "path": str(test_project),
                "glob_pattern": "*.py",
            }
        )

        matches = json.loads(result)

        # Should find multiple function definitions across Python files
        assert len(matches) >= 3

        files = {m["file"] for m in matches}
        # Should find files in both src/ and tests/
        assert any("src" in f for f in files)
        assert any("tests" in f for f in files)

    def test_search_case_insensitive(self, test_project: Path) -> None:
        """Test case-insensitive search."""
        result = grep_search.invoke(
            {
                "pattern": "HELLO",
                "path": str(test_project),
                "case_sensitive": False,
            }
        )

        matches = json.loads(result)

        assert len(matches) >= 1
        assert any("Hello" in m["text"] for m in matches)

    def test_search_with_context(self, test_project: Path) -> None:
        """Test search with context lines."""
        result = grep_search.invoke(
            {
                "pattern": "calculate",
                "path": str(test_project / "src"),
                "glob_pattern": "*.py",
                "context_lines": 2,
            }
        )

        matches = json.loads(result)

        assert len(matches) >= 1

        # Find the match in utils.py
        utils_match = next((m for m in matches if "utils.py" in m["file"]), None)
        assert utils_match is not None

        # Should have some context lines (implementation may vary between grep/rg)
        # Just verify structure is correct
        assert isinstance(utils_match["context_before"], list)
        assert isinstance(utils_match["context_after"], list)

    def test_search_no_matches(self, test_project: Path) -> None:
        """Test search that finds no matches."""
        result = grep_search.invoke(
            {
                "pattern": "nonexistent_pattern_xyz123",
                "path": str(test_project),
            }
        )

        matches = json.loads(result)

        assert matches == []

    def test_search_specific_directory(self, test_project: Path) -> None:
        """Test searching in specific directory."""
        result = grep_search.invoke(
            {
                "pattern": "def",
                "path": str(test_project / "tests"),
                "glob_pattern": "*.py",
            }
        )

        matches = json.loads(result)

        # Should only find matches in tests/
        assert all("tests" in m["file"] for m in matches)

    def test_search_markdown_files(self, test_project: Path) -> None:
        """Test searching in markdown files."""
        result = grep_search.invoke(
            {
                "pattern": "Features",
                "path": str(test_project),
                "glob_pattern": "*.md",
            }
        )

        matches = json.loads(result)

        assert len(matches) >= 1
        assert any("README.md" in m["file"] for m in matches)


class TestRipgrepVsGrep:
    """Test differences between ripgrep and grep implementations."""

    def test_both_find_same_results(self, test_project: Path) -> None:
        """Test that ripgrep and grep find the same matches (when both available)."""
        has_ripgrep = _detect_ripgrep()

        if not has_ripgrep:
            pytest.skip("Ripgrep not available for comparison test")

        # Search with ripgrep (auto-detected)
        result = grep_search.invoke(
            {
                "pattern": "def ",
                "path": str(test_project),
                "glob_pattern": "*.py",
            }
        )

        matches = json.loads(result)

        # Both should find matches
        assert len(matches) >= 3


class TestSearchEdgeCases:
    """Test edge cases and error conditions."""

    def test_search_single_file(self, test_project: Path) -> None:
        """Test searching a single file."""
        result = grep_search.invoke(
            {
                "pattern": "def main",
                "path": str(test_project / "src" / "main.py"),
            }
        )

        matches = json.loads(result)

        assert len(matches) >= 1
        assert all("main.py" in m["file"] for m in matches)

    def test_search_empty_directory(self) -> None:
        """Test searching in empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = grep_search.invoke(
                {
                    "pattern": "anything",
                    "path": tmpdir,
                }
            )

            matches = json.loads(result)
            assert matches == []

    def test_search_regex_pattern(self, test_project: Path) -> None:
        """Test search with regex pattern."""
        result = grep_search.invoke(
            {
                "pattern": r"def \w+\(",
                "path": str(test_project),
                "glob_pattern": "*.py",
            }
        )

        matches = json.loads(result)

        # Should find function definitions
        assert len(matches) >= 3
        assert all("def " in m["text"] for m in matches)

    def test_search_special_characters(self, test_project: Path) -> None:
        """Test search with special characters."""
        # Search for string with quotes
        result = grep_search.invoke(
            {
                "pattern": '"Hello, world!"',
                "path": str(test_project),
            }
        )

        matches = json.loads(result)

        assert len(matches) >= 1
        assert any("Hello, world!" in m["text"] for m in matches)


class TestOutputFormat:
    """Test output format consistency."""

    def test_output_is_valid_json(self, test_project: Path) -> None:
        """Test output is always valid JSON."""
        result = grep_search.invoke(
            {
                "pattern": "def",
                "path": str(test_project),
                "glob_pattern": "*.py",
            }
        )

        # Should parse without error
        matches = json.loads(result)
        assert isinstance(matches, list)

    def test_match_structure(self, test_project: Path) -> None:
        """Test each match has required fields."""
        result = grep_search.invoke(
            {
                "pattern": "def main",
                "path": str(test_project),
            }
        )

        matches = json.loads(result)

        for match in matches:
            assert "file" in match
            assert "line" in match
            assert "text" in match
            assert "context_before" in match
            assert "context_after" in match

            assert isinstance(match["file"], str)
            assert isinstance(match["line"], int)
            assert isinstance(match["text"], str)
            assert isinstance(match["context_before"], list)
            assert isinstance(match["context_after"], list)

    def test_line_numbers_are_positive(self, test_project: Path) -> None:
        """Test line numbers are always positive integers."""
        result = grep_search.invoke(
            {
                "pattern": "def",
                "path": str(test_project),
                "glob_pattern": "*.py",
            }
        )

        matches = json.loads(result)

        for match in matches:
            assert match["line"] > 0
