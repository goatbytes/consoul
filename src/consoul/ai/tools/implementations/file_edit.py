"""File editing tools with line-based editing and security controls.

Provides safe file editing with:
- Line-based editing with exact line-range specifications
- Optimistic locking via expected_hash to prevent concurrent edit conflicts
- Atomic writes (temp file → replace) to prevent file corruption
- Path security validation and extension filtering
- Comprehensive diff previews for all modifications
- Size limits to prevent runaway LLM edits

Note:
    This module implements exact matching only. Progressive matching
    (whitespace/fuzzy tolerance) is implemented in SOUL-106.
    All edit tools are classified as RiskLevel.CAUTION (require approval).
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from consoul.ai.tools.implementations.file_matching import (
    _get_indentation,
    exact_match,
    find_similar_blocks,
    fuzzy_match,
    whitespace_tolerant_match,
)
from consoul.config.models import FileEditToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: FileEditToolConfig | None = None


def set_file_edit_config(config: FileEditToolConfig) -> None:
    """Set the module-level config for file edit tools.

    This should be called by the ToolRegistry when registering file edit tools
    to inject the profile's configured settings.

    Args:
        config: FileEditToolConfig from the active profile's ToolConfig.file_edit
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_file_edit_config() -> FileEditToolConfig:
    """Get the current file edit tool config.

    Returns:
        The configured FileEditToolConfig, or a new default instance if not set.
    """
    return _TOOL_CONFIG if _TOOL_CONFIG is not None else FileEditToolConfig()


@dataclass
class FileEditResult:
    """Result of a file edit operation.

    Contains structured information about the edit including success status,
    metrics, diff preview, and any warnings or errors.

    Attributes:
        status: Operation outcome ("success", "validation_failed", "hash_mismatch", "error")
        bytes_written: Number of bytes written to file (None if not written)
        checksum: SHA256 hex digest of new file content (None if not written)
        changed_lines: List of line ranges that were modified (e.g., ["3-5", "8-9"])
        preview: Unified diff showing changes
        warnings: Non-fatal issues encountered during operation
        error: Error message if status is not "success"
    """

    status: Literal["success", "validation_failed", "hash_mismatch", "error"]
    bytes_written: int | None = None
    checksum: str | None = None
    changed_lines: list[str] | None = None
    preview: str | None = None
    warnings: list[str] | None = None
    error: str | None = None

    def to_json(self) -> str:
        """Convert result to JSON string for tool return value.

        Returns:
            JSON-serialized FileEditResult with None values omitted
        """
        data = {k: v for k, v in asdict(self).items() if v is not None}
        return json.dumps(data, indent=2, ensure_ascii=False)


def _parse_line_range(line_range: str) -> tuple[int, int]:
    """Parse line range string into start and end line numbers.

    Supports single line numbers ("42") and ranges ("1-5").
    Line numbers are 1-indexed as presented to users/LLMs.

    Args:
        line_range: Line range specification ("42" or "1-5")

    Returns:
        Tuple of (start_line, end_line) as 1-indexed integers

    Raises:
        ValueError: If format is invalid or numbers are not positive integers
    """
    line_range = line_range.strip()

    # Check for range format (contains dash)
    # Must handle negative numbers: "5--10" is invalid, "5-10" is valid
    if "-" in line_range and not line_range.startswith("-"):
        # Find first dash that's not at position 0
        parts = line_range.split("-", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid line range format: {line_range}")

        try:
            start = int(parts[0].strip())
            end = int(parts[1].strip())
        except ValueError as e:
            raise ValueError(f"Invalid line numbers in range {line_range}: {e}") from e

        if start < 1 or end < 1:
            raise ValueError(f"Line numbers must be positive: {line_range}")

        return start, end

    # Single line number
    try:
        num = int(line_range)
    except ValueError as e:
        raise ValueError(f"Invalid line number: {line_range}: {e}") from e

    if num < 1:
        raise ValueError(f"Line number must be positive: {line_range}")

    return num, num


def _validate_file_path(
    file_path: str, config: FileEditToolConfig, must_exist: bool = True
) -> Path:
    """Validate file path for security and accessibility.

    Checks for path traversal attempts, blocked paths, and allowed extensions.
    Follows the same security pattern as read.py.

    Args:
        file_path: Path to file to edit/create
        config: FileEditToolConfig with security settings
        must_exist: If True, file must exist. If False, only parent dir must exist.

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path is invalid, blocked, or has disallowed extension
        FileNotFoundError: If file does not exist (when must_exist=True)
    """
    # Check for path traversal attempts BEFORE resolving
    if ".." in file_path:
        raise ValueError("Path traversal (..) not allowed for security")

    # Resolve to absolute path
    path = Path(file_path).resolve()

    # Check if file exists (only if must_exist=True)
    if must_exist:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if it's actually a file (not directory)
        if not path.is_file():
            raise ValueError(f"Not a file: {file_path}")

    # Security: Block paths that match blocked_paths
    # Handle symlink resolution (e.g., /etc → /private/etc on macOS)
    path_str = str(path)
    for blocked in config.blocked_paths:
        # Check both the resolved path and the original path
        if path_str.startswith(blocked) or file_path.startswith(blocked):
            raise ValueError(f"Access denied: Path blocked for security ({blocked})")

    # Validate extension if allowed_extensions is not empty
    if config.allowed_extensions:
        extension = path.suffix.lower()
        # Normalize config extensions to lowercase for case-insensitive comparison
        allowed_lower = [ext.lower() for ext in config.allowed_extensions]

        # Handle extensionless files (empty string in allowed_extensions)
        if extension == "":
            if "" not in allowed_lower:
                raise ValueError(
                    "Extensionless files not allowed (extension filtering enabled)"
                )
        elif extension not in allowed_lower:
            raise ValueError(
                f"File extension {extension} not allowed for editing "
                f"(allowed: {', '.join(config.allowed_extensions)})"
            )

    return path


def _compute_file_hash(path: Path, encoding: str = "utf-8") -> str:
    """Compute SHA256 hash of file content.

    Used for optimistic locking to detect concurrent modifications.

    Args:
        path: Path to file
        encoding: Text encoding (default: utf-8)

    Returns:
        SHA256 hex digest of file content
    """
    # Read as bytes for consistent hashing regardless of line endings
    content_bytes = path.read_bytes()
    return hashlib.sha256(content_bytes).hexdigest()


def _validate_edits(
    line_edits: dict[str, str],
    file_lines: list[str],
    config: FileEditToolConfig,
) -> tuple[bool, str | None]:
    """Validate edit operations before applying.

    Checks for:
    - Edit count limits (max_edits)
    - Payload size limits (max_payload_bytes)
    - Valid line ranges (start <= end, in bounds)
    - Overlapping ranges (ambiguous edits)

    Args:
        line_edits: Dictionary of line range → new content
        file_lines: Current file content as list of lines
        config: FileEditToolConfig with limits

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    # Check max_edits limit
    if len(line_edits) > config.max_edits:
        return (
            False,
            f"Too many edits: {len(line_edits)} exceeds limit of {config.max_edits}",
        )

    # Check max_payload_bytes
    total_bytes = sum(len(content.encode("utf-8")) for content in line_edits.values())
    if total_bytes > config.max_payload_bytes:
        return (
            False,
            f"Payload too large: {total_bytes} bytes exceeds limit of {config.max_payload_bytes}",
        )

    # Parse and validate all line ranges
    parsed_ranges: list[tuple[str, int, int]] = []

    for line_range in line_edits:
        try:
            start, end = _parse_line_range(line_range)
        except ValueError as e:
            return False, str(e)

        # Validate range ordering
        if start > end:
            return (
                False,
                f"Invalid line range {line_range}: start ({start}) > end ({end})",
            )

        # Validate in bounds
        file_line_count = len(file_lines)
        if start < 1:
            return False, f"Invalid line range {line_range}: line {start} < 1"
        if end > file_line_count:
            return (
                False,
                f"Invalid line range {line_range}: line {end} > file length ({file_line_count})",
            )

        parsed_ranges.append((line_range, start, end))

    # Check for overlapping ranges
    for i, (range1, start1, end1) in enumerate(parsed_ranges):
        for range2, start2, end2 in parsed_ranges[i + 1 :]:
            # Ranges overlap if one starts before the other ends
            if (start1 <= start2 <= end1) or (start2 <= start1 <= end2):
                return (
                    False,
                    f"Overlapping line ranges: {range1} and {range2} (ambiguous edit)",
                )

    return True, None


def _apply_line_edits(
    lines: list[str], line_edits: dict[str, str]
) -> tuple[list[str], list[str]]:
    """Apply line-based edits to file content.

    Processes edits from bottom to top (cursor-agent pattern) to preserve
    line numbers. Each edit replaces the specified line range with new content.

    Args:
        lines: Original file content as list of lines (without newlines)
        line_edits: Dictionary of line range → new content

    Returns:
        Tuple of (result_lines, changed_ranges)
        - result_lines: Modified file content as list of lines
        - changed_ranges: List of line ranges that were modified (sorted)
    """
    result_lines = lines.copy()
    changed_ranges: list[str] = []

    # Sort ranges by start line descending (bottom-to-top processing)
    # This prevents index drift: editing line 50 doesn't affect line 10
    sorted_ranges = sorted(
        line_edits.keys(),
        key=lambda r: _parse_line_range(r)[0],
        reverse=True,
    )

    for line_range in sorted_ranges:
        start, end = _parse_line_range(line_range)

        # Convert to 0-indexed
        start_idx = start - 1
        end_idx = end  # Python slice is exclusive at end

        # Get new content and split into lines
        new_content = line_edits[line_range]
        new_lines = new_content.splitlines() if new_content else []

        # Replace the specified lines with new content
        # Example: lines[2:5] = ["a", "b"] replaces lines 3-5 with 2 new lines
        result_lines[start_idx:end_idx] = new_lines

        # Track this change
        changed_ranges.append(line_range)

    # Return changed ranges in sorted order (not reverse)
    changed_ranges.sort(key=lambda r: _parse_line_range(r)[0])

    return result_lines, changed_ranges


def _create_diff_preview(
    original_content: str, new_content: str, file_path: str
) -> str:
    """Generate unified diff preview of changes.

    Args:
        original_content: Original file content
        new_content: Modified file content
        file_path: File path for diff header

    Returns:
        Unified diff as string (empty if no changes)
    """
    import difflib

    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_lines = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )

    return "\n".join(diff_lines)


def _atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write file content atomically using temp file + rename.

    Prevents file corruption if process crashes during write.
    The rename operation is atomic on POSIX systems.

    Args:
        path: Path to file to write
        content: Content to write
        encoding: Text encoding (default: utf-8)

    Raises:
        OSError: If write or rename fails
    """
    # Create temp file in same directory as target
    # (ensures same filesystem for atomic rename)
    # Use random suffix to prevent collisions from concurrent edits
    random_suffix = secrets.token_hex(8)
    temp_path = path.parent / f".{path.name}.{random_suffix}.tmp"

    try:
        # Write to temp file preserving line endings
        # Use newline="" to prevent automatic LF->CRLF conversion on Windows
        with temp_path.open("w", encoding=encoding, newline="") as f:
            f.write(content)

        # Atomic rename (POSIX atomic operation)
        temp_path.replace(path)

    except Exception:
        # Clean up temp file if operation failed
        if temp_path.exists():
            temp_path.unlink()
        raise


class EditFileLinesInput(BaseModel):
    """Input schema for edit_file_lines tool."""

    file_path: str = Field(description="Absolute or relative path to file to edit")
    line_edits: dict[str, str] = Field(
        description=(
            "Line edits as dictionary with line ranges as keys. "
            'Examples: {"1-5": "new content for lines 1-5", "8": "single line 8", "10-12": "three\\nlines\\nhere"}. '
            "Line numbers are 1-indexed. Ranges are inclusive. Empty string deletes lines."
        )
    )
    expected_hash: str | None = Field(
        None,
        description=(
            "SHA256 hash of file content for optimistic locking. "
            "If provided and file content has changed, edit will fail with hash_mismatch. "
            "Get hash from read_file result or previous edit_file_lines result."
        ),
    )
    dry_run: bool = Field(
        False,
        description="If true, preview changes without modifying file. Returns diff preview only.",
    )


@tool(args_schema=EditFileLinesInput)
def edit_file_lines(
    file_path: str,
    line_edits: dict[str, str],
    expected_hash: str | None = None,
    dry_run: bool = False,
) -> str:
    """Edit file using line-range specifications.

    Performs precise, atomic line-based edits on text files. Edits are applied
    bottom-to-top to preserve line numbers. Supports optimistic locking to prevent
    concurrent modifications.

    Examples:
        Edit single line:
        >>> edit_file_lines("config.py", {"5": "DEBUG = True"})

        Edit range:
        >>> edit_file_lines("app.py", {"10-15": "# Refactored section\\ndef new_func():\\n    pass"})

        Multiple edits:
        >>> edit_file_lines("main.py", {"1-3": "#!/usr/bin/env python3", "20": "# Updated"})

        With optimistic lock:
        >>> edit_file_lines("data.json", {"1": "{"}, expected_hash="abc123...")

        Preview only:
        >>> edit_file_lines("test.txt", {"5-10": "new content"}, dry_run=True)

    Args:
        file_path: Path to file (absolute or relative)
        line_edits: Dictionary mapping line ranges to new content
        expected_hash: Optional SHA256 hash for optimistic locking
        dry_run: If true, preview changes without writing

    Returns:
        JSON string with FileEditResult:
        {
            "status": "success" | "validation_failed" | "hash_mismatch" | "error",
            "bytes_written": 1234,  // Only if written
            "checksum": "sha256hex...",  // Only if written
            "changed_lines": ["3-5", "8-9"],
            "preview": "unified diff...",
            "warnings": ["warning1", ...]
        }

    Note:
        Line numbers are 1-indexed. Ranges are inclusive.
        Edits are processed bottom-to-top to avoid index drift.
        Empty string as new content deletes the specified lines.
    """
    config = get_file_edit_config()
    warnings: list[str] = []

    try:
        # Validate that line_edits is actually a dict with string keys and values
        if not isinstance(line_edits, dict):
            return FileEditResult(
                status="validation_failed",
                error=f"line_edits must be a dictionary, got {type(line_edits).__name__}",
            ).to_json()

        # Validate all keys and values are strings
        for key, value in line_edits.items():
            if not isinstance(key, str):
                return FileEditResult(
                    status="validation_failed",
                    error=f"line_edits keys must be strings, got {type(key).__name__} for key {key!r}",
                ).to_json()
            if not isinstance(value, str):
                return FileEditResult(
                    status="validation_failed",
                    error=f"line_edits values must be strings, got {type(value).__name__} for key {key!r}",
                ).to_json()

        # 1. Validate file path (security checks, extension filtering)
        try:
            path = _validate_file_path(file_path, config, must_exist=True)
        except (ValueError, FileNotFoundError) as e:
            return FileEditResult(
                status="validation_failed",
                error=f"Path validation failed: {e}",
            ).to_json()

        # 2. Read current file content preserving line endings
        # Use newline="" to prevent automatic CRLF->LF conversion
        try:
            with path.open("r", encoding=config.default_encoding, newline="") as f:
                original_content = f.read()
        except UnicodeDecodeError:
            return FileEditResult(
                status="error",
                error=f"File encoding error: Cannot decode {file_path} as {config.default_encoding}",
            ).to_json()
        except OSError as e:
            return FileEditResult(
                status="error",
                error=f"Failed to read file: {e}",
            ).to_json()

        # Detect newline style to preserve it
        # Check for CRLF first (Windows), then LF (Unix), default to LF
        if "\r\n" in original_content:
            newline_char = "\r\n"
        elif "\n" in original_content:
            newline_char = "\n"
        else:
            # File has no newlines (single line or empty)
            newline_char = "\n"

        original_lines = original_content.splitlines()

        # 3. Check optimistic lock if expected_hash provided
        if expected_hash:
            current_hash = _compute_file_hash(path, config.default_encoding)
            if current_hash != expected_hash:
                return FileEditResult(
                    status="hash_mismatch",
                    error=(
                        f"File changed since read (hash mismatch). "
                        f"Expected {expected_hash[:16]}..., got {current_hash[:16]}... "
                        f"Re-read file and retry edit."
                    ),
                    checksum=current_hash,
                ).to_json()

        # 4. Validate edits (count limits, size limits, range validity)
        is_valid, validation_error = _validate_edits(line_edits, original_lines, config)
        if not is_valid:
            return FileEditResult(
                status="validation_failed",
                error=validation_error,
            ).to_json()

        # 5. Apply edits (bottom-to-top processing)
        new_lines, changed_ranges = _apply_line_edits(original_lines, line_edits)

        # Reconstruct content using detected newline style
        # Preserve final newline if original had one
        if original_content.endswith(("\n", "\r\n")):
            new_content = newline_char.join(new_lines) + newline_char
        else:
            new_content = newline_char.join(new_lines)

        # 6. Generate diff preview
        preview = _create_diff_preview(original_content, new_content, str(path))

        # 7. If dry run, return preview without writing
        if dry_run:
            warnings.append("Dry run - no changes written to file")
            return FileEditResult(
                status="success",
                changed_lines=changed_ranges,
                preview=preview,
                warnings=warnings,
            ).to_json()

        # 8. Atomic write
        try:
            _atomic_write(path, new_content, config.default_encoding)
        except OSError as e:
            return FileEditResult(
                status="error",
                error=f"Failed to write file: {e}",
                preview=preview,
                changed_lines=changed_ranges,
            ).to_json()

        # 9. Compute new checksum
        checksum = _compute_file_hash(path, config.default_encoding)
        bytes_written = len(new_content.encode(config.default_encoding))

        # 10. Return success result
        return FileEditResult(
            status="success",
            bytes_written=bytes_written,
            checksum=checksum,
            changed_lines=changed_ranges,
            preview=preview,
            warnings=warnings if warnings else None,
        ).to_json()

    except Exception as e:
        # Catch-all for unexpected errors
        return FileEditResult(
            status="error",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        ).to_json()


class CreateFileInput(BaseModel):
    """Input schema for create_file tool.

    CRITICAL: When creating JSON/YAML/TOML files, the 'content' field MUST be a STRING.
    Convert objects to strings first using json.dumps(), yaml.dump(), or similar.

    Correct usage for JSON file:
        {
            "file_path": "config.json",
            "content": "{\\"name\\": \\"myapp\\", \\"version\\": \\"1.0.0\\"}"
        }

    WRONG usage (will fail validation):
        {
            "file_path": "config.json",
            "content": {"name": "myapp", "version": "1.0.0"}  # ❌ dict instead of string
        }
    """

    file_path: str = Field(
        description=(
            "Absolute or relative path to the file to create. "
            "Examples: 'package.json', 'src/utils.py', 'config/settings.yaml'"
        )
    )
    content: str = Field(
        description=(
            "File content AS A STRING (not a dict/object). "
            "For JSON: use json.dumps(your_dict). "
            "For YAML: use yaml.dump(your_dict). "
            "For code/text: use raw string with newlines (\\n)"
        )
    )
    overwrite: bool = Field(
        default=False,
        description=(
            "Allow overwriting existing file. "
            "Requires both overwrite=True AND config.allow_overwrite=True."
        ),
    )
    dry_run: bool = Field(
        default=False,
        description="If True, preview changes without modifying file",
    )


@tool(args_schema=CreateFileInput)
def create_file(
    file_path: str,
    content: str,
    overwrite: bool = False,
    dry_run: bool = False,
) -> str:
    """Create new file with content.

    Creates parent directories automatically if they don't exist.
    Protects against accidental overwrites unless both overwrite=True
    and config.allow_overwrite=True.

    IMPORTANT: This function requires TWO separate arguments:
    1. file_path (string): The path where the file should be created
    2. content (string): The actual file content as a STRING

    Common mistakes to avoid:
    - Do NOT pass file content as a dict/object - convert to string first
    - For JSON files: use json.dumps() to convert dict to string
    - For YAML/TOML: convert to string representation first
    - Always provide both file_path AND content as separate parameters

    Args:
        file_path: Absolute or relative path to file to create (e.g., "package.json", "src/config.yaml")
        content: Content to write to the file AS A STRING (e.g., '{"name": "myapp"}' not {"name": "myapp"})
        overwrite: Allow overwriting existing file (requires config approval too)
        dry_run: If True, preview changes without modifying file

    Returns:
        JSON-serialized FileEditResult with:
        - status: "success" | "validation_failed" | "error"
        - checksum: SHA256 hex digest of written content
        - bytes_written: Size of content in bytes
        - preview: Unified diff preview (when dry_run=True)
        - error: Error message if status is not success

    Examples:
        Creating a Python file:
        >>> create_file(file_path="src/utils.py", content="def add(a, b):\\n    return a + b")

        Creating a JSON file (note: content is a STRING):
        >>> import json
        >>> config_data = {"name": "myapp", "version": "1.0.0"}
        >>> create_file(file_path="package.json", content=json.dumps(config_data, indent=2))

        Creating a text file:
        >>> create_file(file_path="README.md", content="# My Project\\n\\nDescription here")

        With overwrite protection:
        >>> create_file(file_path="data.txt", content="new content", overwrite=True)
    """
    try:
        # Validate input types early with helpful error messages
        if not isinstance(file_path, str):
            return FileEditResult(
                status="validation_failed",
                error=(
                    f"file_path must be a string, got {type(file_path).__name__}. "
                    "Example: file_path='package.json'"
                ),
            ).to_json()

        if not isinstance(content, str):
            return FileEditResult(
                status="validation_failed",
                error=(
                    f"content must be a string, got {type(content).__name__}. "
                    "If creating a JSON file, use json.dumps() to convert your dict to a string first. "
                    "Example: content=json.dumps({{'name': 'myapp'}}, indent=2)"
                ),
            ).to_json()

        config = get_file_edit_config()

        # Validate path (allow non-existent for creation)
        path = _validate_file_path(file_path, config, must_exist=False)

        # Check payload size limit
        encoding = config.default_encoding
        payload_bytes = len(content.encode(encoding))
        if payload_bytes > config.max_payload_bytes:
            return FileEditResult(
                status="validation_failed",
                error=(
                    f"Content size ({payload_bytes:,} bytes) exceeds maximum allowed "
                    f"({config.max_payload_bytes:,} bytes)"
                ),
            ).to_json()

        # Check if file exists
        file_exists = path.exists()

        # Overwrite protection: both flags must be True
        if file_exists and not (overwrite and config.allow_overwrite):
            error_msg = f"File already exists: {file_path}. "
            if not overwrite:
                error_msg += "Use overwrite=True to replace existing file."
            elif not config.allow_overwrite:
                error_msg += (
                    "Config does not allow overwrites (config.allow_overwrite=False)."
                )

            return FileEditResult(
                status="validation_failed",
                error=error_msg,
            ).to_json()

        # If dry_run, generate preview and return without modifying file
        if dry_run:
            # For new files, show all content with "new file" marker
            # For overwrites, show diff from existing content
            if file_exists:
                original_content = path.read_text(encoding=encoding)
                preview = _create_diff_preview(original_content, content, str(path))
            else:
                # New file - create diff showing all new content
                preview = _create_diff_preview("", content, str(path))

            return FileEditResult(
                status="success",
                bytes_written=payload_bytes,
                preview=preview,
            ).to_json()

        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write using existing helper
        _atomic_write(path, content, encoding=encoding)

        # Compute checksum
        checksum = _compute_file_hash(path, encoding=encoding)

        # Return success result (use "success" to match FileEditResult contract)
        return FileEditResult(
            status="success",
            bytes_written=payload_bytes,
            checksum=checksum,
        ).to_json()

    except (ValueError, FileNotFoundError) as e:
        # Validation errors (path security, extension, blocked paths)
        return FileEditResult(
            status="validation_failed",
            error=str(e),
        ).to_json()

    except Exception as e:
        # Catch-all for unexpected errors (I/O, encoding, etc.)
        return FileEditResult(
            status="error",
            error=f"Failed to create file: {type(e).__name__}: {e}",
        ).to_json()


class SearchReplaceEdit(BaseModel):
    """A single search/replace operation.

    Attributes:
        search: Text to search for (can be multi-line)
        replace: Replacement text
    """

    search: str = Field(description="Text to search for in the file")
    replace: str = Field(description="Replacement text")


class EditFileSearchReplaceInput(BaseModel):
    """Input schema for edit_file_search_replace tool."""

    file_path: str = Field(description="Absolute or relative path to file to edit")
    edits: list[SearchReplaceEdit] = Field(
        description="List of search/replace operations to apply"
    )
    tolerance: Literal["strict", "whitespace", "fuzzy"] = Field(
        default="strict",
        description=(
            "Matching tolerance level:\n"
            "- strict: Exact byte-for-byte matching only\n"
            "- whitespace: Ignore leading/trailing whitespace\n"
            "- fuzzy: Allow similarity-based matching (80%+ threshold)"
        ),
    )
    expected_hash: str | None = Field(
        default=None,
        description="Expected SHA256 hash for optimistic locking (optional)",
    )
    dry_run: bool = Field(
        default=False,
        description="If True, preview changes without modifying file",
    )


@tool(args_schema=EditFileSearchReplaceInput)
def edit_file_search_replace(
    file_path: str,
    edits: list[dict[str, str]],
    tolerance: Literal["strict", "whitespace", "fuzzy"] = "strict",
    expected_hash: str | None = None,
    dry_run: bool = False,
) -> str:
    """Edit file using search/replace blocks with progressive matching.

    Searches for text blocks and replaces them with new content. Supports
    progressive matching strategies:
    - strict: Exact matching only
    - whitespace: Tolerates indentation differences, auto-fixes indentation
    - fuzzy: Allows typos/minor differences (80%+ similarity threshold)

    When exact match fails, tries more tolerant strategies based on tolerance
    setting. Returns warnings for non-exact matches.

    Args:
        file_path: Absolute or relative path to file
        edits: List of {"search": "...", "replace": "..."} dictionaries
        tolerance: Matching tolerance level (default: "strict")
        expected_hash: Expected file SHA256 hash for conflict detection (optional)
        dry_run: If True, return preview without modifying file

    Returns:
        JSON-serialized FileEditResult with:
        - status: "success" | "validation_failed" | "hash_mismatch" | "error"
        - checksum: SHA256 hex digest of new file content
        - bytes_written: Size of new file in bytes
        - preview: Unified diff showing changes
        - warnings: List of warnings (e.g., "Fuzzy matched (85% confidence)")
        - error: Error message if status is not success

    Raises:
        NoMatchError: When search text not found (with "Did you mean?" suggestions)
        AmbiguousMatchError: When search text appears multiple times

    Example:
        >>> result = edit_file_search_replace.invoke({
        ...     "file_path": "src/main.py",
        ...     "edits": [{
        ...         "search": "def old_function():\\n    pass",
        ...         "replace": "def new_function():\\n    return True"
        ...     }],
        ...     "tolerance": "whitespace"
        ... })
        >>> data = json.loads(result)
        >>> data["status"]
        'success'
    """
    try:
        config = get_file_edit_config()

        # 1. Validate file path
        path = _validate_file_path(file_path, config, must_exist=True)

        # 2. Read current file content preserving line endings
        try:
            with path.open("r", encoding=config.default_encoding, newline="") as f:
                original_content = f.read()
        except UnicodeDecodeError:
            return FileEditResult(
                status="error",
                error=f"File encoding error: Cannot decode {file_path} as {config.default_encoding}",
            ).to_json()

        # Detect newline style
        if "\r\n" in original_content:
            newline_char = "\r\n"
        elif "\n" in original_content:
            newline_char = "\n"
        else:
            newline_char = "\n"

        original_lines = original_content.split(newline_char)
        # Remove trailing empty string if content ended with newline
        # This prevents double newlines when reconstructing
        if (
            original_content.endswith(newline_char)
            and original_lines
            and original_lines[-1] == ""
        ):
            original_lines = original_lines[:-1]

        # 3. Check optimistic lock if provided
        if expected_hash is not None:
            actual_hash = _compute_file_hash(path, encoding=config.default_encoding)
            if actual_hash != expected_hash:
                return FileEditResult(
                    status="hash_mismatch",
                    error=(
                        f"File changed since read: expected hash {expected_hash[:8]}... "
                        f"but got {actual_hash[:8]}..."
                    ),
                ).to_json()

        # 4. Validate edit count and payload size
        if len(edits) > config.max_edits:
            return FileEditResult(
                status="validation_failed",
                error=f"Too many edits: {len(edits)} exceeds limit of {config.max_edits}",
            ).to_json()

        total_payload = sum(
            len(edit["replace"].encode("utf-8"))
            if isinstance(edit, dict)
            else len(edit.replace.encode("utf-8"))
            for edit in edits
        )
        if total_payload > config.max_payload_bytes:
            return FileEditResult(
                status="validation_failed",
                error=(
                    f"Payload too large: {total_payload:,} bytes exceeds "
                    f"limit of {config.max_payload_bytes:,} bytes"
                ),
            ).to_json()

        # 5. Process each search/replace edit with progressive matching
        warnings: list[str] = []
        replacements: list[
            tuple[int, int, str]
        ] = []  # (start_line, end_line, new_content)

        for i, edit in enumerate(edits):
            # Handle both dict and Pydantic object
            if isinstance(edit, dict):
                search_text = edit["search"]
                replace_text = edit["replace"]
            else:
                search_text = edit.search
                replace_text = edit.replace

            if not search_text:
                return FileEditResult(
                    status="validation_failed",
                    error=f"Edit {i + 1}: search text cannot be empty",
                ).to_json()

            search_lines = search_text.split("\n")

            # Progressive matching
            match = None
            try:
                # Try exact match first (always)
                matches = exact_match(original_lines, search_lines)
                if matches:
                    if len(matches) > 1:
                        # Ambiguous - multiple exact matches
                        locations = ", ".join(
                            f"lines {m.start_line}-{m.end_line}" for m in matches
                        )
                        return FileEditResult(
                            status="validation_failed",
                            error=(
                                f"Edit {i + 1}: Ambiguous search - found {len(matches)} matches at {locations}. "
                                "Please be more specific."
                            ),
                        ).to_json()
                    match = matches[0]

                # Whitespace-tolerant second (only if no exact match)
                if not match and tolerance in ["whitespace", "fuzzy"]:
                    matches = whitespace_tolerant_match(original_lines, search_lines)
                    if matches:
                        if len(matches) > 1:
                            locations = ", ".join(
                                f"lines {m.start_line}-{m.end_line}" for m in matches
                            )
                            return FileEditResult(
                                status="validation_failed",
                                error=(
                                    f"Edit {i + 1}: Ambiguous search - found {len(matches)} matches at {locations}. "
                                    "Please be more specific."
                                ),
                            ).to_json()
                        match = matches[0]
                        warnings.append(
                            f"Edit {i + 1}: Matched ignoring indentation differences"
                        )

                        # Auto-fix indentation in replacement
                        # Strategy: For each line, copy the indentation from the corresponding
                        # matched file line, preserving the indentation structure
                        if match.indentation_offset != 0:
                            replace_lines = replace_text.split("\n")
                            matched_file_lines = match.matched_lines
                            normalized_lines = []

                            for i, replace_line in enumerate(replace_lines):
                                stripped_replace = replace_line.lstrip()
                                if not stripped_replace:  # Empty line
                                    normalized_lines.append("")
                                    continue

                                # If we have a corresponding matched line, copy its indentation
                                if i < len(matched_file_lines):
                                    matched_line = matched_file_lines[i]
                                    # Extract indentation from matched file line
                                    file_indent_count, file_indent_char = (
                                        _get_indentation(matched_line)
                                    )
                                    file_indent_str = (
                                        file_indent_char * file_indent_count
                                    )
                                    normalized_lines.append(
                                        file_indent_str + stripped_replace
                                    )
                                else:
                                    # Extra lines in replacement - use same indentation as last matched line
                                    if matched_file_lines:
                                        last_indent_count, last_indent_char = (
                                            _get_indentation(matched_file_lines[-1])
                                        )
                                        last_indent_str = (
                                            last_indent_char * last_indent_count
                                        )
                                        normalized_lines.append(
                                            last_indent_str + stripped_replace
                                        )
                                    else:
                                        normalized_lines.append(stripped_replace)

                            replace_text = "\n".join(normalized_lines)

                # Fuzzy third (only if no exact or whitespace match)
                if not match and tolerance == "fuzzy":
                    matches = fuzzy_match(original_lines, search_lines, threshold=0.8)
                    if matches:
                        if len(matches) > 1:
                            locations = ", ".join(
                                f"lines {m.start_line}-{m.end_line}" for m in matches
                            )
                            return FileEditResult(
                                status="validation_failed",
                                error=(
                                    f"Edit {i + 1}: Ambiguous search - found {len(matches)} matches at {locations}. "
                                    "Please be more specific."
                                ),
                            ).to_json()
                        match = matches[0]
                        warnings.append(
                            f"Edit {i + 1}: Fuzzy matched ({match.confidence:.0%} confidence)"
                        )

                # No match found
                if not match:
                    # Generate suggestions
                    similar = find_similar_blocks(original_lines, search_lines, top_n=3)
                    if similar and similar[0].similarity > 0.5:
                        suggestions = []
                        for block in similar[:3]:
                            suggestions.append(
                                f"  - Lines {block.start_line}-{block.end_line} "
                                f"({block.similarity:.0%} similar)"
                            )
                        suggestion_text = "\n".join(suggestions)
                        return FileEditResult(
                            status="validation_failed",
                            error=(
                                f"Edit {i + 1}: Search text not found. Did you mean:\n{suggestion_text}"
                            ),
                        ).to_json()
                    else:
                        return FileEditResult(
                            status="validation_failed",
                            error=f"Edit {i + 1}: Search text not found in file",
                        ).to_json()

                # Record replacement (will be applied bottom-to-top later)
                replacements.append((match.start_line, match.end_line, replace_text))

            except Exception as e:
                return FileEditResult(
                    status="error",
                    error=f"Edit {i + 1}: {type(e).__name__}: {e}",
                ).to_json()

        # 6. Check for overlapping replacements
        replacements.sort(key=lambda r: r[0])
        for i in range(len(replacements) - 1):
            if replacements[i][1] >= replacements[i + 1][0]:
                return FileEditResult(
                    status="validation_failed",
                    error="Overlapping search/replace blocks (edits conflict)",
                ).to_json()

        # 7. Apply replacements bottom-to-top (preserves line numbers)
        result_lines = original_lines.copy()
        for start_line, end_line, replace_text in reversed(replacements):
            replace_lines = replace_text.split("\n")
            # Replace lines (convert from 1-indexed to 0-indexed)
            result_lines[start_line - 1 : end_line] = replace_lines

        # 8. Reconstruct content with original newline style
        if original_content.endswith(("\n", "\r\n")):
            new_content = newline_char.join(result_lines) + newline_char
        else:
            new_content = newline_char.join(result_lines)

        # 9. Create diff preview
        preview = _create_diff_preview(
            original_content, new_content, file_path=str(path)
        )

        # 10. Write file if not dry run
        if not dry_run:
            _atomic_write(path, new_content, encoding=config.default_encoding)
            checksum = _compute_file_hash(path, encoding=config.default_encoding)
            bytes_written = len(new_content.encode(config.default_encoding))
        else:
            checksum = None
            bytes_written = None

        # Return success result
        return FileEditResult(
            status="success",
            bytes_written=bytes_written,
            checksum=checksum,
            preview=preview,
            warnings=warnings if warnings else None,
        ).to_json()

    except (ValueError, FileNotFoundError) as e:
        return FileEditResult(
            status="validation_failed",
            error=str(e),
        ).to_json()

    except Exception as e:
        return FileEditResult(
            status="error",
            error=f"Failed to edit file: {type(e).__name__}: {e}",
        ).to_json()


class DeleteFileInput(BaseModel):
    """Input schema for delete_file tool."""

    file_path: str = Field(description="Absolute or relative path to file to delete")
    dry_run: bool = Field(
        default=False,
        description="If True, preview changes without modifying file",
    )


class AppendToFileInput(BaseModel):
    """Input schema for append_to_file tool."""

    file_path: str = Field(description="Absolute or relative path to file")
    content: str = Field(description="Content to append to end of file")
    create_if_missing: bool = Field(
        default=False,
        description="Create file if it doesn't exist. If False, returns error when file missing.",
    )
    dry_run: bool = Field(
        default=False,
        description="If True, preview changes without modifying file",
    )


@tool(args_schema=DeleteFileInput)
def delete_file(file_path: str, dry_run: bool = False) -> str:
    """Delete file (DANGEROUS - always requires approval).

    Deletes the specified file after validation checks. This operation
    is classified as DANGEROUS and requires user approval even in
    permissive approval modes.

    Args:
        file_path: Absolute or relative path to file to delete
        dry_run: If True, preview changes without modifying file

    Returns:
        JSON-serialized result with:
        - status: "deleted" | "validation_failed" | "error"
        - path: Absolute path that was deleted
        - timestamp: ISO format deletion timestamp for audit trail
        - preview: Diff showing file deletion (when dry_run=True)
        - error: Error message if status is not "deleted"

    Example:
        >>> result = delete_file.invoke({"file_path": "temp/old_file.txt"})
        >>> data = json.loads(result)
        >>> data["status"]
        'deleted'
        >>> data["path"]
        '/abs/path/to/temp/old_file.txt'
    """
    try:
        from datetime import datetime, timezone

        config = get_file_edit_config()

        # Validate path (must exist for deletion)
        path = _validate_file_path(file_path, config, must_exist=True)

        # If dry_run, generate preview and return without modifying file
        if dry_run:
            # Read existing content to show what will be deleted
            original_content = path.read_text(encoding=config.default_encoding)
            # Create diff showing file deletion (original -> empty)
            preview = _create_diff_preview(original_content, "", str(path))

            return FileEditResult(
                status="success",
                preview=preview,
            ).to_json()

        # Delete the file
        path.unlink()

        # Return tombstone entry for audit trail
        return json.dumps(
            {
                "status": "deleted",
                "path": str(path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        )

    except FileNotFoundError as e:
        # File doesn't exist
        return FileEditResult(
            status="validation_failed",
            error=str(e),
        ).to_json()

    except ValueError as e:
        # Path security validation failed (traversal, blocked path, extension)
        return FileEditResult(
            status="validation_failed",
            error=str(e),
        ).to_json()

    except Exception as e:
        # Catch-all for unexpected errors (permission denied, I/O errors, etc.)
        return FileEditResult(
            status="error",
            error=f"Failed to delete file: {type(e).__name__}: {e}",
        ).to_json()


@tool(args_schema=AppendToFileInput)
def append_to_file(
    file_path: str,
    content: str,
    create_if_missing: bool = False,
    dry_run: bool = False,
) -> str:
    """Append content to end of file.

    Appends content to the end of an existing file with smart newline handling.
    Can optionally create the file if it doesn't exist.

    Args:
        file_path: Absolute or relative path to file
        content: Content to append to end of file
        create_if_missing: Create file if it doesn't exist (default: False)
        dry_run: If True, preview changes without modifying file

    Returns:
        JSON-serialized FileEditResult with:
        - status: "success" | "validation_failed" | "error"
        - checksum: SHA256 hex digest of final file content
        - bytes_written: Total size of final file in bytes
        - preview: Unified diff preview (when dry_run=True)
        - error: Error message if status is not success

    Example:
        >>> result = append_to_file.invoke({
        ...     "file_path": "logs/app.log",
        ...     "content": "New log entry",
        ...     "create_if_missing": True,
        ... })
        >>> data = json.loads(result)
        >>> data["status"]
        'success'
    """
    try:
        config = get_file_edit_config()

        # Validate path (allow non-existent if create_if_missing=True)
        path = _validate_file_path(file_path, config, must_exist=False)

        # Check if file exists
        file_exists = path.exists()

        if not file_exists:
            if not create_if_missing:
                return FileEditResult(
                    status="validation_failed",
                    error=f"File not found: {file_path}. Set create_if_missing=True to create it.",
                ).to_json()

            # For dry_run, don't create directories yet
            original_content = ""
        else:
            # Read existing content preserving line endings (newline="" preserves CRLF/LF)
            with path.open("r", encoding=config.default_encoding, newline="") as f:
                original_content = f.read()

        # Smart newline separator:
        # - Empty file: no separator
        # - Ends with newline: no separator
        # - Doesn't end with newline: add separator matching file's line ending convention
        if original_content and not original_content.endswith(("\n", "\r\n")):
            # Detect line ending convention from existing content
            separator = "\r\n" if "\r\n" in original_content else "\n"
        else:
            separator = ""

        # Combine with new content
        final_content = original_content + separator + content

        # Check payload size limit (final size)
        payload_bytes = len(final_content.encode(config.default_encoding))
        if payload_bytes > config.max_payload_bytes:
            return FileEditResult(
                status="validation_failed",
                error=(
                    f"Final file size ({payload_bytes:,} bytes) would exceed maximum allowed "
                    f"({config.max_payload_bytes:,} bytes)"
                ),
            ).to_json()

        # If dry_run, generate preview and return without modifying file
        if dry_run:
            preview = _create_diff_preview(original_content, final_content, str(path))
            return FileEditResult(
                status="success",
                bytes_written=payload_bytes,
                preview=preview,
            ).to_json()

        # Create parent directories if needed (only when actually writing)
        if not file_exists:
            path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        _atomic_write(path, final_content, encoding=config.default_encoding)

        # Compute checksum of final content
        checksum = _compute_file_hash(path, encoding=config.default_encoding)

        # Return success result
        return FileEditResult(
            status="success",
            bytes_written=payload_bytes,
            checksum=checksum,
        ).to_json()

    except FileNotFoundError as e:
        # Path validation failed (parent directory doesn't exist)
        return FileEditResult(
            status="validation_failed",
            error=str(e),
        ).to_json()

    except ValueError as e:
        # Path security validation failed
        return FileEditResult(
            status="validation_failed",
            error=str(e),
        ).to_json()

    except Exception as e:
        # Catch-all for unexpected errors
        return FileEditResult(
            status="error",
            error=f"Failed to append to file: {type(e).__name__}: {e}",
        ).to_json()
