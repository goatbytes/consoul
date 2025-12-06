"""Utilities for reading and formatting file content in CLI commands.

This module provides functions for reading text files and PDFs, formatting them
for inclusion in AI conversation context. It handles:
- File reading with encoding detection and fallback
- PDF text extraction with page markers
- Binary file detection and rejection (except PDFs)
- Glob pattern expansion with limits
- Size limit enforcement (per-file and total)
- Line numbering for code references
- XML-style formatting for clear context boundaries
"""

from __future__ import annotations

import glob as glob_module
from pathlib import Path


def _is_pdf_file(path: Path) -> bool:
    """Check if file is a PDF by extension.

    Args:
        path: Path to file to check

    Returns:
        True if file has .pdf extension
    """
    return path.suffix.lower() == ".pdf"


def _read_pdf(path: Path, max_pages: int = 50) -> str:
    """Read PDF file and extract text with page markers.

    Args:
        path: Path to PDF file
        max_pages: Maximum number of pages to read (default: 50)

    Returns:
        Extracted text with page markers, formatted as:
        === Page 1 ===
        <text from page 1>

        === Page 2 ===
        <text from page 2>

    Raises:
        ValueError: If PDF cannot be read or pypdf is not installed
    """
    # Try to import pypdf
    try:
        import pypdf
    except ImportError:
        raise ValueError(
            "PDF support requires 'pypdf' library. "
            "Install with: pip install 'consoul[pdf]'"
        ) from None

    try:
        # Open PDF reader
        reader = pypdf.PdfReader(str(path))
        total_pages = len(reader.pages)

        if total_pages == 0:
            return "[PDF contains no pages]"

        # Apply page limit
        pages_to_read = min(total_pages, max_pages)

        # Extract text from pages
        result = []
        for page_num in range(pages_to_read):
            page = reader.pages[page_num]
            text = page.extract_text()

            # Add page marker
            page_header = f"=== Page {page_num + 1} ==="
            result.append(page_header)
            result.append(text.strip() if text else "[No text on this page]")

        # Join with blank lines between pages
        extracted_text = "\n\n".join(result)

        # Add truncation notice if needed
        if pages_to_read < total_pages:
            extracted_text += (
                f"\n\n[Truncated: showing {pages_to_read} of {total_pages} pages. "
                f"Use --file with individual pages or increase max_pages.]"
            )

        return extracted_text

    except pypdf.errors.PdfReadError as e:
        raise ValueError(
            f"Failed to read PDF. File may be corrupted or encrypted: {e}"
        ) from e
    except Exception as e:
        raise ValueError(f"Error reading PDF: {e}") from e


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


def read_file_content(
    file_path: Path,
    max_size: int = 100_000,
    include_line_numbers: bool = True,
) -> str:
    """Read and format single file content (text files and PDFs).

    Args:
        file_path: Path to file to read
        max_size: Maximum file size in bytes (default: 100KB)
        include_line_numbers: Whether to add line numbers for text files (default: True)

    Returns:
        Formatted file content as string

    Raises:
        ValueError: If file is binary (except PDF), too large, or cannot be read
    """
    # Check file exists and is readable
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    # Check if PDF file first (before size check, before binary check)
    if _is_pdf_file(file_path):
        return _read_pdf(file_path, max_pages=50)

    # Check file size (for text files)
    file_size = file_path.stat().st_size
    if file_size > max_size:
        raise ValueError(
            f"File {file_path.name} exceeds size limit: "
            f"{file_size:,} bytes (max: {max_size:,} bytes)"
        )

    # Check if binary (non-PDF files only)
    if _is_binary_file(file_path):
        raise ValueError(
            f"Binary files are not supported: {file_path.name} (except PDFs)"
        )

    # Read file content with encoding fallback
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            # Try with error handling
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise ValueError(f"Cannot read file {file_path.name}: {e}") from e

    # Add line numbers if requested
    if include_line_numbers:
        lines = content.splitlines()
        # Calculate padding for line numbers
        num_lines = len(lines)
        padding = len(str(num_lines))

        numbered_lines = []
        for i, line in enumerate(lines, start=1):
            numbered_lines.append(f"{i:>{padding}}→{line}")

        content = "\n".join(numbered_lines)

    return content


def expand_glob_pattern(
    pattern: str,
    max_files: int = 50,
    base_dir: Path | None = None,
) -> list[Path]:
    """Expand glob pattern to list of file paths.

    Args:
        pattern: Glob pattern (e.g., "*.py", "src/**/*.ts")
        max_files: Maximum files to return (default: 50)
        base_dir: Base directory for relative patterns (default: current dir)

    Returns:
        List of resolved file paths matching the pattern

    Raises:
        ValueError: If pattern matches too many files
    """
    # Use base_dir if provided, otherwise current directory
    if base_dir is None:
        base_dir = Path.cwd()

    # Expand glob pattern (recursive if ** present)
    if "**" in pattern:
        matches = glob_module.glob(pattern, recursive=True)
    else:
        matches = glob_module.glob(pattern)

    # Convert to Path objects and filter to files only
    file_paths = []
    for match in matches:
        path = Path(match).resolve()
        if path.is_file():
            file_paths.append(path)

    # Enforce file count limit
    if len(file_paths) > max_files:
        raise ValueError(
            f"Glob pattern '{pattern}' matched {len(file_paths)} files "
            f"(max: {max_files}). Use more specific patterns."
        )

    # Sort for deterministic order
    return sorted(file_paths)


def format_files_context(
    file_paths: list[Path],
    max_total_size: int = 500_000,
) -> str:
    """Format multiple files into context block for AI conversation.

    Args:
        file_paths: List of file paths to include
        max_total_size: Maximum total size across all files (default: 500KB)

    Returns:
        Formatted context string with all file contents

    Raises:
        ValueError: If total size exceeds limit or files cannot be read
    """
    if not file_paths:
        return ""

    formatted_blocks = []
    total_size = 0

    for file_path in file_paths:
        # Read file content
        try:
            content = read_file_content(file_path, max_size=100_000)
        except ValueError as e:
            # Re-raise with context
            raise ValueError(f"Error reading {file_path.name}: {e}") from e

        # Check total size limit
        content_size = len(content.encode("utf-8"))
        if total_size + content_size > max_total_size:
            raise ValueError(
                f"Total file content exceeds size limit: "
                f"{(total_size + content_size):,} bytes (max: {max_total_size:,} bytes). "
                f"Failed at file: {file_path.name}"
            )

        total_size += content_size

        # Format with XML-style tags and path
        formatted = f'<file path="{file_path}">\n{content}\n</file>'
        formatted_blocks.append(formatted)

    # Join all blocks with blank line separator
    return "\n\n".join(formatted_blocks)
