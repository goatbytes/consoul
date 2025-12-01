"""Tool call formatting utilities for TUI display.

Provides formatting functions for tool calls with argument visibility,
used for displaying tool execution in a minimal, readable format.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text

__all__ = ["format_tool_header"]


# Mapping of tool names to user-friendly display names
TOOL_DISPLAY_NAMES = {
    "bash_execute": "Bash",
    "read_file": "Read",
    "write_file": "Write",
    "edit_file": "Edit",
    "create_file": "Create",
    "grep_search": "Search",
    "code_search": "Search",
    "ripgrep_search": "Search",
    "web_search": "Web Search",
    "wikipedia_search": "Wikipedia",
}


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
        Text('⛏ Bash("ls -la")')

        >>> format_tool_header("read_file", {"path": "/path/to/file.txt"})
        Text('⛏ Read("/path/to/file.txt")')

        >>> format_tool_header("grep_search", {"pattern": "TODO", "path": "src/"})
        Text('⛏ Search("TODO", in="src/")')
    """
    header = Text()
    header.append("⛏ ", style="bold")

    # Get friendly display name
    display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)

    # Format based on tool type
    if tool_name == "bash_execute" and "command" in arguments:
        # Show bash command inline with quotes
        cmd = arguments["command"]
        truncated = _truncate_arg(cmd, max_len=80)
        header.append(f'{display_name}("', style="bold cyan")
        header.append(truncated, style="cyan")
        header.append('")', style="bold cyan")

    elif tool_name in ("read_file", "write_file", "edit_file", "create_file"):
        # File operations - show file_path or path prominently
        # Try file_path first (used by read_file, write_file, create_file)
        # then fall back to path (used by edit_file)
        path_key = None
        if "file_path" in arguments:
            path_key = "file_path"
        elif "path" in arguments:
            path_key = "path"

        if path_key:
            path = arguments[path_key]
            truncated_path = _truncate_arg(str(path), max_len=60)
            header.append(f'{display_name}("', style="bold cyan")
            header.append(truncated_path, style="cyan")
            header.append('")', style="bold cyan")
        else:
            # Fallback to generic format
            header.append(f"{display_name}(", style="bold cyan")
            header.append(_format_generic_header(tool_name, arguments), style="cyan")
            header.append(")", style="bold cyan")

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
            header.append(f'{display_name}("', style="bold cyan")
            # Show path if present
            if "path" in arguments:
                path = _truncate_arg(str(arguments["path"]), max_len=30)
                header.append(truncated_pattern, style="cyan")
                header.append('", in="', style="bold cyan")
                header.append(path, style="cyan")
                header.append('")', style="bold cyan")
            else:
                header.append(truncated_pattern, style="cyan")
                header.append('")', style="bold cyan")
        else:
            # Fallback to generic format
            header.append(f"{display_name}(", style="bold cyan")
            header.append(_format_generic_header(tool_name, arguments), style="cyan")
            header.append(")", style="bold cyan")

    elif len(arguments) == 1:
        # Single argument - show inline with quotes
        key, value = next(iter(arguments.items()))
        truncated = _truncate_arg(str(value), max_len=60)
        header.append(f'{display_name}("', style="bold cyan")
        header.append(truncated, style="cyan")
        header.append('")', style="bold cyan")

    else:
        # Multiple arguments - show abbreviated
        header.append(f"{display_name}(", style="bold cyan")
        header.append(_format_generic_header(tool_name, arguments), style="cyan")
        header.append(")", style="bold cyan")

    return header
