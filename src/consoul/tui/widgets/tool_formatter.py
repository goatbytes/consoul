"""Tool call formatting utilities for TUI display.

Provides formatting functions for tool calls with argument visibility,
used for displaying tool execution in a minimal, readable format.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text

__all__ = ["format_tool_header"]


def _truncate_arg(value: str, max_len: int) -> str:
    """Truncate argument value to maximum length with ellipsis.

    Args:
        value: Argument value to truncate
        max_len: Maximum length before truncation

    Returns:
        Truncated string with '...' if longer than max_len
    """
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _format_generic_header(tool_name: str, arguments: dict[str, Any]) -> str:
    """Format header for tools with multiple/generic arguments.

    Args:
        tool_name: Name of the tool
        arguments: Tool arguments dictionary

    Returns:
        String with tool name and abbreviated argument list
    """
    if not arguments:
        return f"{tool_name}()"

    # Show first 3 argument names with ellipsis
    args_preview = ", ".join(f"{k}=..." for k in list(arguments.keys())[:3])
    if len(arguments) > 3:
        args_preview += ", ..."
    return f"{tool_name}({args_preview})"


def format_tool_header(tool_name: str, arguments: dict[str, Any]) -> Text:
    """Format tool header with tool name and arguments.

    Shows arguments inline in the header for immediate visibility
    of what the tool is executing. Different formatting strategies
    are used based on tool type and argument complexity.

    Args:
        tool_name: Name of the tool being executed
        arguments: Tool arguments dictionary

    Returns:
        Rich Text object with formatted header

    Examples:
        >>> format_tool_header("bash_execute", {"command": "ls -la"})
        Text('🔧 bash_execute("ls -la")')

        >>> format_tool_header("read_file", {"path": "/path/to/file.txt"})
        Text('🔧 read_file(path="/path/to/file.txt")')

        >>> format_tool_header("grep_search", {"pattern": "TODO", "path": "src/"})
        Text('🔧 grep_search(pattern="TODO", path="src/")')
    """
    header = Text()
    header.append("🔧 ", style="bold")

    # Format based on tool type
    if tool_name == "bash_execute" and "command" in arguments:
        # Show bash command inline
        cmd = arguments["command"]
        truncated = _truncate_arg(cmd, max_len=80)
        header.append(f'bash_execute("{truncated}")', style="bold cyan")

    elif tool_name in ("read_file", "write_file", "edit_file"):
        # File operations - show path prominently
        if "path" in arguments:
            path = arguments["path"]
            truncated_path = _truncate_arg(str(path), max_len=60)
            # Show other args abbreviated
            other_args = [k for k in arguments if k != "path"]
            if other_args:
                args_str = f'path="{truncated_path}", {", ".join(f"{k}=..." for k in other_args[:2])}'
            else:
                args_str = f'path="{truncated_path}"'
            header.append(f"{tool_name}({args_str})", style="bold cyan")
        else:
            # Fallback to generic format
            header.append(
                _format_generic_header(tool_name, arguments), style="bold cyan"
            )

    elif tool_name in (
        "grep_search",
        "code_search",
        "ripgrep_search",
        "search",
    ):
        # Search tools - show pattern/query prominently
        pattern_key = None
        for key in ["pattern", "query", "search_term", "term"]:
            if key in arguments:
                pattern_key = key
                break

        if pattern_key:
            pattern = arguments[pattern_key]
            truncated_pattern = _truncate_arg(str(pattern), max_len=50)
            # Show path if present
            if "path" in arguments:
                path = _truncate_arg(str(arguments["path"]), max_len=30)
                args_str = f'{pattern_key}="{truncated_pattern}", path="{path}"'
            else:
                args_str = f'{pattern_key}="{truncated_pattern}"'
            header.append(f"{tool_name}({args_str})", style="bold cyan")
        else:
            # Fallback to generic format
            header.append(
                _format_generic_header(tool_name, arguments), style="bold cyan"
            )

    elif len(arguments) == 1:
        # Single argument - show inline
        key, value = next(iter(arguments.items()))
        truncated = _truncate_arg(str(value), max_len=60)
        header.append(f'{tool_name}({key}="{truncated}")', style="bold cyan")

    else:
        # Multiple arguments - show abbreviated
        header.append(_format_generic_header(tool_name, arguments), style="bold cyan")

    return header
