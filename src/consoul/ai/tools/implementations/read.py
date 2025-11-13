"""Read file tool with line numbering and security controls.

Provides safe file reading with:
- Line-numbered output (cat -n style)
- Offset/limit parameters for large files
- Encoding fallback for non-UTF-8 files
- Path security validation
- Extension filtering
- Clear error messages

Note:
    This tool is classified as RiskLevel.SAFE since it's read-only and
    requires no user approval (matching Claude Code behavior).
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from consoul.config.models import ReadToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: ReadToolConfig | None = None


def set_read_config(config: ReadToolConfig) -> None:
    """Set the module-level config for read tool.

    This should be called by the ToolRegistry when registering read_file
    to inject the profile's configured settings.

    Args:
        config: ReadToolConfig from the active profile's ToolConfig.read
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_read_config() -> ReadToolConfig:
    """Get the current read tool config.

    Returns:
        The configured ReadToolConfig, or a new default instance if not set.
    """
    return _TOOL_CONFIG if _TOOL_CONFIG is not None else ReadToolConfig()


def _is_binary_file(path: Path) -> bool:
    """Check if file is likely binary by looking for null bytes.

    Args:
        path: Path to file to check

    Returns:
        True if file appears to be binary, False otherwise
    """
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)  # Read first 8KB
            return b"\x00" in chunk
    except Exception:
        return False


def _validate_path(file_path: str, config: ReadToolConfig) -> Path:
    """Validate file path for security and accessibility.

    Args:
        file_path: Path to file to read
        config: ReadToolConfig with security settings

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path is invalid, blocked, or inaccessible
    """
    # Check for path traversal attempts BEFORE resolving
    if ".." in file_path:
        raise ValueError("Path traversal (..) not allowed for security")

    # Resolve to absolute path
    path = Path(file_path).resolve()

    # Check blocked paths BEFORE checking existence
    # This prevents probing for file existence in blocked locations
    # Check both resolved path and original path (for symlink cases like /etc -> /private/etc on macOS)
    path_str = str(path)
    for blocked in config.blocked_paths:
        # Resolve blocked path too for comparison
        blocked_resolved = (
            str(Path(blocked).resolve()) if Path(blocked).exists() else blocked
        )
        if (
            path_str.startswith(blocked)
            or path_str.startswith(blocked_resolved)
            or file_path.startswith(blocked)
        ):
            raise ValueError(
                f"Reading from {blocked} is not allowed for security reasons"
            )

    # Check if file exists
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")

    # Check if it's a directory
    if path.is_dir():
        raise ValueError(
            f"Cannot read directory: {file_path}. Specify a file path instead."
        )

    return path


def _validate_extension(path: Path, config: ReadToolConfig) -> None:
    """Validate file extension against allowed list.

    Args:
        path: Path to file to check
        config: ReadToolConfig with allowed_extensions list

    Raises:
        ValueError: If extension is not in allowed list (when list is non-empty)
    """
    # Empty allowed_extensions means allow all
    if not config.allowed_extensions:
        return

    suffix = path.suffix.lower()
    if suffix not in config.allowed_extensions:
        raise ValueError(
            f"File extension '{suffix}' not allowed. "
            f"Allowed extensions: {', '.join(config.allowed_extensions)}"
        )


def _read_with_encoding_fallback(path: Path) -> str:
    """Read file with encoding fallback chain.

    Tries UTF-8 first, then UTF-8 with BOM, then Latin-1 as last resort.

    Args:
        path: Path to file to read

    Returns:
        File contents as string

    Raises:
        UnicodeDecodeError: If all encoding attempts fail
    """
    encodings = ["utf-8", "utf-8-sig", "latin-1"]

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            if encoding == "latin-1":  # Last resort - should never fail
                raise
            continue  # Try next encoding

    # Should never reach here since latin-1 accepts all byte sequences
    raise UnicodeDecodeError("unknown", b"", 0, 1, "All encoding attempts failed")


def _format_with_line_numbers(lines: list[str], start_line: int = 1) -> str:
    """Format lines with line numbers (cat -n style).

    Args:
        lines: List of lines to format
        start_line: Starting line number (1-indexed)

    Returns:
        Formatted string with line numbers

    Example:
        >>> _format_with_line_numbers(["hello", "world"], start_line=1)
        '     1\thello\\n     2\tworld'
    """
    result = []
    for i, line in enumerate(lines, start=start_line):
        # Remove trailing newline if present (we'll add consistent formatting)
        content = line.rstrip("\n\r")
        result.append(f"{i:6d}\t{content}")
    return "\n".join(result)


class ReadFileInput(BaseModel):
    """Input schema for read_file tool."""

    file_path: str = Field(description="Path to the file to read")
    offset: int | None = Field(
        None,
        description="Starting line number (1-indexed) for reading a subset of lines",
        gt=0,
    )
    limit: int | None = Field(
        None,
        description="Number of lines to read (if offset is provided)",
        gt=0,
    )


@tool(args_schema=ReadFileInput)  # type: ignore[misc]
def read_file(
    file_path: str,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    """Read file contents with line numbers and line-range control.

    This tool reads text files and returns their contents with 1-based line
    numbers prefixed to each line (cat -n style). It supports reading specific
    line ranges for large files and handles various encodings gracefully.

    Security features:
    - Blocks reading from sensitive system paths (/etc/shadow, /proc, /dev, /sys)
    - Validates file extensions against allowed list
    - Prevents path traversal attacks (..)
    - Detects and rejects binary files

    The tool uses ReadToolConfig from the active profile's ToolConfig.read
    settings. Call set_read_config() to inject the profile configuration before
    tool registration.

    Args:
        file_path: Path to the file to read (absolute or relative)
        offset: Optional starting line number (1-indexed). If provided, reads
                from this line onwards.
        limit: Optional number of lines to read. If not provided and offset is
               specified, uses max_lines_default from config. If neither offset
               nor limit is specified, reads entire file.

    Returns:
        File contents with line numbers. Format:
        - Success: "     1\t<line1>\\n     2\t<line2>..."
        - Empty file: "[File is empty]"
        - Error: "❌ <error message>"

    Example:
        >>> read_file("src/main.py")
        '     1\timport os\\n     2\timport sys\\n...'
        >>> read_file("src/main.py", offset=10, limit=5)
        '    10\tdef main():\\n    11\t    pass\\n...'
    """
    # Get config from module-level (set by registry via set_read_config)
    config = get_read_config()

    try:
        # Validate path for security
        path = _validate_path(file_path, config)

        # Validate extension
        _validate_extension(path, config)

        # Check if binary file
        if _is_binary_file(path):
            return "❌ Unsupported binary file format. This tool only reads text files."

        # Read file with encoding fallback
        try:
            content = _read_with_encoding_fallback(path)
        except UnicodeDecodeError:
            return (
                f"❌ Failed to decode file {file_path}. "
                "File may be binary or use an unsupported encoding."
            )
        except PermissionError:
            return f"❌ Permission denied: {file_path}"

        # Handle empty file
        if not content:
            return "[File is empty]"

        # Split into lines (preserving line breaks for now)
        lines = content.splitlines(keepends=True)

        # Determine line range to read
        if offset is not None:
            # Convert 1-indexed offset to 0-indexed
            start_idx = offset - 1

            # Validate offset is within file bounds
            if start_idx >= len(lines):
                return (
                    f"❌ Offset {offset} exceeds file length ({len(lines)} lines). "
                    f"File has only {len(lines)} lines."
                )

            # Determine how many lines to read
            if limit is not None:
                end_idx = start_idx + limit
            else:
                # Use max_lines_default from config if no limit specified
                end_idx = start_idx + config.max_lines_default

            # Slice lines
            lines = lines[start_idx:end_idx]

            # Format with line numbers starting at offset
            return _format_with_line_numbers(lines, start_line=offset)
        else:
            # No offset specified - read from beginning
            if limit is not None:
                # Limit number of lines
                lines = lines[:limit]
            # else: read entire file

            # Format with line numbers starting at 1
            return _format_with_line_numbers(lines, start_line=1)

    except ValueError as e:
        # Security validation or other expected errors
        return f"❌ {e}"
    except FileNotFoundError:
        return f"❌ File not found: {file_path}"
    except Exception as e:
        # Unexpected errors
        return f"❌ Error reading file: {e}"
