"""Text search tool with ripgrep and grep support.

Provides fast regex-based text search with:
- Ripgrep (rg) for high performance JSON output
- Automatic fallback to grep if ripgrep unavailable
- Glob pattern filtering
- Case sensitivity control
- Context lines (before/after)
- Normalized JSON output format

Example:
    >>> from consoul.ai.tools.implementations.grep_search import grep_search
    >>> result = grep_search(
    ...     pattern="def main",
    ...     path="src/",
    ...     glob_pattern="*.py",
    ...     case_sensitive=False,
    ... )
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.config.models import GrepSearchToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: GrepSearchToolConfig | None = None


def set_grep_search_config(config: GrepSearchToolConfig) -> None:
    """Set the module-level config for grep_search tool.

    This should be called by the ToolRegistry when registering grep_search
    to inject the profile's configured settings.

    Args:
        config: GrepSearchToolConfig from the active profile's ToolConfig.grep_search
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_grep_search_config() -> GrepSearchToolConfig:
    """Get the current grep_search tool config.

    Returns:
        The configured GrepSearchToolConfig, or a new default instance if not set.
    """
    return _TOOL_CONFIG if _TOOL_CONFIG is not None else GrepSearchToolConfig()


def _detect_ripgrep() -> bool:
    """Detect if ripgrep (rg) is available on the system.

    Returns:
        True if ripgrep is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["rg", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _build_ripgrep_command(
    pattern: str,
    path: str,
    glob_pattern: str | None = None,
    case_sensitive: bool = True,
    context_lines: int = 0,
) -> list[str]:
    """Build ripgrep command with parameters.

    Args:
        pattern: Regex pattern to search for
        path: Directory or file path to search
        glob_pattern: Optional glob pattern to filter files (e.g., "*.py")
        case_sensitive: Whether search is case-sensitive
        context_lines: Number of context lines before/after matches

    Returns:
        List of command arguments for subprocess
    """
    cmd = ["rg", "--json", pattern, path]

    if glob_pattern:
        cmd.extend(["--glob", glob_pattern])

    if not case_sensitive:
        cmd.append("-i")

    if context_lines > 0:
        cmd.extend(["-C", str(context_lines)])

    return cmd


def _build_grep_command(
    pattern: str,
    path: str,
    glob_pattern: str | None = None,
    case_sensitive: bool = True,
    context_lines: int = 0,
) -> list[str]:
    """Build grep command with parameters.

    Args:
        pattern: Regex pattern to search for
        path: Directory or file path to search
        glob_pattern: Optional glob pattern to filter files (e.g., "*.py")
        case_sensitive: Whether search is case-sensitive
        context_lines: Number of context lines before/after matches

    Returns:
        List of command arguments for subprocess
    """
    cmd = ["grep", "-rn", pattern, path]

    if glob_pattern:
        cmd.extend(["--include", glob_pattern])

    if not case_sensitive:
        cmd.append("-i")

    if context_lines > 0:
        cmd.extend(["-C", str(context_lines)])

    return cmd


def _parse_ripgrep_output(output: str, context_lines: int = 0) -> list[dict[str, Any]]:
    """Parse ripgrep JSON output into normalized format.

    Args:
        output: Raw JSON output from ripgrep
        context_lines: Number of context lines requested (used for buffer sizing)

    Returns:
        List of match dictionaries with normalized structure:
        {
            "file": "path/to/file.py",
            "line": 42,
            "text": "matching line content",
            "context_before": ["line 40", "line 41"],
            "context_after": ["line 43", "line 44"]
        }
    """
    results: list[dict[str, Any]] = []
    context_before: list[str] = []
    context_after: list[str] = []
    collecting_after = False
    current_match: dict[str, Any] | None = None

    for line in output.strip().split("\n"):
        if not line.strip():
            continue

        try:
            entry = json.loads(line)
            entry_type = entry.get("type")

            if entry_type == "match":
                # Save previous match with collected context
                if current_match:
                    current_match["context_before"] = list(context_before)
                    current_match["context_after"] = list(context_after)
                    results.append(current_match)
                    context_before = []
                    context_after = []
                    collecting_after = False  # Reset flag for next match

                data = entry["data"]
                current_match = {
                    "file": data["path"]["text"],
                    "line": data["line_number"],
                    "text": data["lines"]["text"].rstrip("\n"),
                    "context_before": [],
                    "context_after": [],
                }
                collecting_after = True

            elif entry_type == "context":
                data = entry["data"]
                context_text = data["lines"]["text"].rstrip("\n")

                if current_match and collecting_after:
                    context_after.append(context_text)
                else:
                    context_before.append(context_text)
                    # Keep only last N context lines (N = context_lines requested)
                    if context_lines > 0 and len(context_before) > context_lines:
                        context_before.pop(0)

        except (json.JSONDecodeError, KeyError):
            # Skip malformed JSON lines
            continue

    # Add final match
    if current_match:
        current_match["context_before"] = list(context_before)
        current_match["context_after"] = list(context_after)
        results.append(current_match)

    return results


def _parse_grep_output(output: str, context_lines: int = 0) -> list[dict[str, Any]]:
    """Parse grep line-based output into normalized format.

    Args:
        output: Raw line-based output from grep
        context_lines: Number of context lines to expect

    Returns:
        List of match dictionaries with normalized structure
    """
    results: list[dict[str, Any]] = []
    lines = output.strip().split("\n")

    # Regex to parse grep output: file:line:text or file-line-text (context)
    match_pattern = re.compile(r"^(.+?):(\d+):(.*)$")
    context_pattern = re.compile(r"^(.+?)-(\d+)-(.*)$")

    current_match: dict[str, Any] | None = None
    context_before: list[str] = []

    for line in lines:
        if not line.strip() or line == "--":
            # Separator between match groups
            if current_match:
                results.append(current_match)
                current_match = None
                context_before = []
            continue

        # Try to parse as match line
        match = match_pattern.match(line)
        if match:
            # Save previous match
            if current_match:
                results.append(current_match)

            file_path, line_num, text = match.groups()
            current_match = {
                "file": file_path,
                "line": int(line_num),
                "text": text,
                "context_before": list(context_before),
                "context_after": [],
            }
            context_before = []
            continue

        # Try to parse as context line
        context_match = context_pattern.match(line)
        if context_match:
            _, _, text = context_match.groups()
            if current_match:
                # Context after match
                current_match["context_after"].append(text)
            else:
                # Context before next match
                context_before.append(text)
                # Keep only last N context lines
                if len(context_before) > context_lines:
                    context_before.pop(0)

    # Add final match
    if current_match:
        results.append(current_match)

    return results


def _execute_search(
    pattern: str,
    path: str,
    glob_pattern: str | None = None,
    case_sensitive: bool = True,
    context_lines: int = 0,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Execute text search using ripgrep or grep.

    Args:
        pattern: Regex pattern to search for
        path: Directory or file path to search
        glob_pattern: Optional glob pattern to filter files
        case_sensitive: Whether search is case-sensitive
        context_lines: Number of context lines before/after matches
        timeout: Timeout in seconds

    Returns:
        List of normalized match dictionaries

    Raises:
        ToolExecutionError: If search execution fails
    """
    # Validate path exists
    search_path = Path(path)
    if not search_path.exists():
        raise ToolExecutionError(f"Search path does not exist: {path}")

    # Detect and use ripgrep if available
    use_ripgrep = _detect_ripgrep()

    try:
        if use_ripgrep:
            cmd = _build_ripgrep_command(
                pattern,
                path,
                glob_pattern,
                case_sensitive,
                context_lines,
            )
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # ripgrep returns exit code 1 when no matches found (not an error)
            if result.returncode not in (0, 1):
                raise ToolExecutionError(
                    f"Ripgrep failed with code {result.returncode}: {result.stderr}"
                )

            return _parse_ripgrep_output(result.stdout, context_lines)

        else:
            # Fallback to grep
            cmd = _build_grep_command(
                pattern,
                path,
                glob_pattern,
                case_sensitive,
                context_lines,
            )
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # grep returns exit code 1 when no matches found (not an error)
            if result.returncode not in (0, 1):
                raise ToolExecutionError(
                    f"Grep failed with code {result.returncode}: {result.stderr}"
                )

            return _parse_grep_output(result.stdout, context_lines)

    except subprocess.TimeoutExpired as e:
        raise ToolExecutionError(
            f"Search timed out after {timeout} seconds: {pattern}"
        ) from e
    except Exception as e:
        raise ToolExecutionError(f"Search execution failed: {e}") from e


@tool
def grep_search(
    pattern: str,
    path: str = ".",
    glob_pattern: str | None = None,
    case_sensitive: bool = True,
    context_lines: int = 0,
    timeout: int | None = None,
) -> str:
    """Search for text patterns in files using ripgrep or grep.

    Fast regex-based text search with automatic ripgrep/grep detection.
    Returns JSON formatted results with file paths, line numbers, and context.

    Args:
        pattern: Regex pattern to search for
        path: Directory or file path to search (default: current directory)
        glob_pattern: Optional glob pattern to filter files (e.g., "*.py", "*.{js,ts}")
        case_sensitive: Whether search is case-sensitive (default: True)
        context_lines: Number of context lines before/after matches (default: 0)
        timeout: Search timeout in seconds (default: from config or 30)

    Returns:
        JSON string with search results:
        [
            {
                "file": "path/to/file.py",
                "line": 42,
                "text": "matching line content",
                "context_before": ["line 40", "line 41"],
                "context_after": ["line 43", "line 44"]
            },
            ...
        ]

    Raises:
        ToolExecutionError: If search fails or path doesn't exist

    Example:
        >>> grep_search("def main", path="src/", glob_pattern="*.py")
        '[{"file": "src/main.py", "line": 10, "text": "def main():", ...}]'
    """
    config = get_grep_search_config()

    # Use config timeout if not specified
    if timeout is None:
        timeout = config.timeout

    # Execute search
    results = _execute_search(
        pattern=pattern,
        path=path,
        glob_pattern=glob_pattern,
        case_sensitive=case_sensitive,
        context_lines=context_lines,
        timeout=timeout,
    )

    # Return JSON formatted results
    return json.dumps(results, indent=2)
