"""Tests for tool discovery module."""

from pathlib import Path
from textwrap import dedent

from langchain_core.tools import tool

from consoul.ai.tools.base import RiskLevel
from consoul.ai.tools.discovery import (
    _is_tool,
    _load_tools_from_file,
    discover_tools_from_directory,
)


class TestIsTool:
    """Test _is_tool helper function."""

    def test_valid_tool_function(self) -> None:
        """Test that @tool decorated function is recognized."""

        @tool
        def my_test_tool(query: str) -> str:
            """Test tool."""
            return f"Result: {query}"

        assert _is_tool(my_test_tool) is True

    def test_non_tool_function(self) -> None:
        """Test that regular function is not recognized as tool."""

        def regular_function(x: int) -> int:
            return x * 2

        assert _is_tool(regular_function) is False

    def test_non_tool_object(self) -> None:
        """Test that random object is not recognized as tool."""
        assert _is_tool("string") is False
        assert _is_tool(123) is False
        assert _is_tool([1, 2, 3]) is False
        assert _is_tool({"key": "value"}) is False

    def test_class_not_recognized(self) -> None:
        """Test that classes are not recognized as tools (only instances)."""

        class MyClass:
            name = "test"

            def run(self) -> str:
                return "result"

        assert _is_tool(MyClass) is False


class TestLoadToolsFromFile:
    """Test _load_tools_from_file function."""

    def test_load_valid_tool(self, tmp_path: Path) -> None:
        """Test loading a file with a valid tool."""
        tool_file = tmp_path / "my_tool.py"
        tool_file.write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def my_custom_tool(query: str) -> str:
                    '''Custom tool for testing.'''
                    return f'Result: {query}'
            """)
        )

        tools = _load_tools_from_file(tool_file)

        assert len(tools) == 1
        tool_obj, risk_level = tools[0]
        assert tool_obj.name == "my_custom_tool"
        assert risk_level == RiskLevel.CAUTION

    def test_load_multiple_tools(self, tmp_path: Path) -> None:
        """Test loading a file with multiple tools."""
        tool_file = tmp_path / "tools.py"
        tool_file.write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def tool_one(x: int) -> int:
                    '''First tool.'''
                    return x * 2

                @tool
                def tool_two(y: str) -> str:
                    '''Second tool.'''
                    return y.upper()

                @tool
                def tool_three(z: float) -> float:
                    '''Third tool.'''
                    return z / 2
            """)
        )

        tools = _load_tools_from_file(tool_file)

        assert len(tools) == 3
        tool_names = {tool.name for tool, _ in tools}
        assert tool_names == {"tool_one", "tool_two", "tool_three"}

    def test_load_file_with_non_tools(self, tmp_path: Path) -> None:
        """Test that non-tool objects are ignored."""
        tool_file = tmp_path / "mixed.py"
        tool_file.write_text(
            dedent("""
                from langchain_core.tools import tool

                # Regular variables and functions
                CONSTANT = 42

                def helper_function(x: int) -> int:
                    return x + 1

                class MyClass:
                    pass

                # Actual tool
                @tool
                def actual_tool(query: str) -> str:
                    '''The only tool.'''
                    return query
            """)
        )

        tools = _load_tools_from_file(tool_file)

        assert len(tools) == 1
        assert tools[0][0].name == "actual_tool"

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        """Test that syntax errors are handled gracefully."""
        tool_file = tmp_path / "bad_syntax.py"
        tool_file.write_text("def bad syntax here:")

        tools = _load_tools_from_file(tool_file)

        assert tools == []

    def test_import_error_returns_empty(self, tmp_path: Path) -> None:
        """Test that import errors are handled gracefully."""
        tool_file = tmp_path / "bad_import.py"
        tool_file.write_text("from nonexistent_module import something")

        tools = _load_tools_from_file(tool_file)

        assert tools == []

    def test_runtime_error_returns_empty(self, tmp_path: Path) -> None:
        """Test that runtime errors during import are handled."""
        tool_file = tmp_path / "runtime_error.py"
        tool_file.write_text(
            dedent("""
                raise RuntimeError("This module raises an error on import")
            """)
        )

        tools = _load_tools_from_file(tool_file)

        assert tools == []


class TestDiscoverToolsFromDirectory:
    """Test discover_tools_from_directory function."""

    def test_discover_from_empty_directory(self, tmp_path: Path) -> None:
        """Test discovering from empty directory."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        tools = discover_tools_from_directory(tools_dir)

        assert tools == []

    def test_discover_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test discovering from directory that doesn't exist."""
        nonexistent = tmp_path / "nonexistent"

        tools = discover_tools_from_directory(nonexistent)

        assert tools == []

    def test_discover_file_not_directory(self, tmp_path: Path) -> None:
        """Test that providing a file path instead of directory returns empty."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("not a directory")

        tools = discover_tools_from_directory(file_path)

        assert tools == []

    def test_discover_single_tool_file(self, tmp_path: Path) -> None:
        """Test discovering a single tool from a file."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        tool_file = tools_dir / "my_tool.py"
        tool_file.write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def search_tool(query: str) -> str:
                    '''Search for something.'''
                    return f'Searching: {query}'
            """)
        )

        tools = discover_tools_from_directory(tools_dir)

        assert len(tools) == 1
        assert tools[0][0].name == "search_tool"
        assert tools[0][1] == RiskLevel.CAUTION

    def test_discover_multiple_files(self, tmp_path: Path) -> None:
        """Test discovering tools from multiple files."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create multiple tool files
        (tools_dir / "tool1.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def tool_alpha(x: str) -> str:
                    '''Tool alpha.'''
                    return x
            """)
        )

        (tools_dir / "tool2.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def tool_beta(y: int) -> int:
                    '''Tool beta.'''
                    return y
            """)
        )

        (tools_dir / "tool3.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def tool_gamma(z: float) -> float:
                    '''Tool gamma.'''
                    return z
            """)
        )

        tools = discover_tools_from_directory(tools_dir)

        assert len(tools) == 3
        tool_names = {tool.name for tool, _ in tools}
        assert tool_names == {"tool_alpha", "tool_beta", "tool_gamma"}

    def test_discover_recursive(self, tmp_path: Path) -> None:
        """Test recursive discovery in subdirectories."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create nested structure
        subdir = tools_dir / "subdir"
        subdir.mkdir()

        (tools_dir / "top_level.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def top_tool(x: str) -> str:
                    '''Top level tool.'''
                    return x
            """)
        )

        (subdir / "nested.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def nested_tool(y: str) -> str:
                    '''Nested tool.'''
                    return y
            """)
        )

        tools = discover_tools_from_directory(tools_dir, recursive=True)

        assert len(tools) == 2
        tool_names = {tool.name for tool, _ in tools}
        assert tool_names == {"top_tool", "nested_tool"}

    def test_discover_non_recursive(self, tmp_path: Path) -> None:
        """Test non-recursive discovery (only top level)."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create nested structure
        subdir = tools_dir / "subdir"
        subdir.mkdir()

        (tools_dir / "top_level.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def top_tool(x: str) -> str:
                    '''Top level tool.'''
                    return x
            """)
        )

        (subdir / "nested.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def nested_tool(y: str) -> str:
                    '''Nested tool.'''
                    return y
            """)
        )

        tools = discover_tools_from_directory(tools_dir, recursive=False)

        assert len(tools) == 1
        assert tools[0][0].name == "top_tool"

    def test_skip_init_files(self, tmp_path: Path) -> None:
        """Test that __init__.py files are skipped."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        (tools_dir / "__init__.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def init_tool(x: str) -> str:
                    '''Init tool.'''
                    return x
            """)
        )

        (tools_dir / "regular.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def regular_tool(y: str) -> str:
                    '''Regular tool.'''
                    return y
            """)
        )

        tools = discover_tools_from_directory(tools_dir)

        # Should only find regular_tool, not init_tool
        assert len(tools) == 1
        assert tools[0][0].name == "regular_tool"

    def test_skip_private_files(self, tmp_path: Path) -> None:
        """Test that private files (_file.py) are skipped."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        (tools_dir / "_private.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def private_tool(x: str) -> str:
                    '''Private tool.'''
                    return x
            """)
        )

        (tools_dir / "public.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def public_tool(y: str) -> str:
                    '''Public tool.'''
                    return y
            """)
        )

        tools = discover_tools_from_directory(tools_dir)

        assert len(tools) == 1
        assert tools[0][0].name == "public_tool"

    def test_handle_files_with_errors(self, tmp_path: Path) -> None:
        """Test that files with errors don't break discovery of other files."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Good file
        (tools_dir / "good.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def good_tool(x: str) -> str:
                    '''Good tool.'''
                    return x
            """)
        )

        # Bad syntax
        (tools_dir / "bad_syntax.py").write_text("def bad syntax:")

        # Bad import
        (tools_dir / "bad_import.py").write_text("from nonexistent import tool")

        tools = discover_tools_from_directory(tools_dir)

        # Should still find the good tool
        assert len(tools) == 1
        assert tools[0][0].name == "good_tool"

    def test_string_path_argument(self, tmp_path: Path) -> None:
        """Test that string path works as well as Path object."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        (tools_dir / "tool.py").write_text(
            dedent("""
                from langchain_core.tools import tool

                @tool
                def string_path_tool(x: str) -> str:
                    '''String path tool.'''
                    return x
            """)
        )

        # Use string path
        tools = discover_tools_from_directory(str(tools_dir))

        assert len(tools) == 1
        assert tools[0][0].name == "string_path_tool"
