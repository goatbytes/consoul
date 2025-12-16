"""Image path detection and validation utilities for TUI messages.

This module provides utilities for detecting image file references in user messages
and validating them before processing. Supports natural language references like:
- "What's in screenshot.png?"
- "Compare design_v1.png design_v2.jpg"
- "Analyze [diagram.webp] and explain"
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = [
    "extract_image_paths",
    "format_message_with_indicators",
    "validate_image_path",
]

# Supported image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

# Regex pattern to match image file paths
# Matches: filename.ext, ./path/file.ext, /absolute/path/file.ext
# Supports: brackets [file.png], quotes "file.png", and standalone paths
IMAGE_PATH_PATTERN = re.compile(
    r'[\["]?(\S+\.(?:png|jpg|jpeg|gif|webp|bmp))[\]"]?', re.IGNORECASE
)


def extract_image_paths(message: str) -> tuple[str, list[str]]:
    """Extract and validate image file paths from message text.

    Detects image references in the message, validates that they exist,
    and returns both the original message and a list of valid image paths.

    Args:
        message: User message text that may contain image path references

    Returns:
        Tuple of (original_message, list_of_valid_image_paths)
        The message is returned unchanged. Validation results are in the list.

    Example:
        >>> extract_image_paths("What's in screenshot.png?")
        ("What's in screenshot.png?", ["/absolute/path/to/screenshot.png"])

        >>> extract_image_paths("Compare img1.png img2.jpg")
        ("Compare img1.png img2.jpg", ["/path/to/img1.png", "/path/to/img2.jpg"])

        >>> extract_image_paths("Hello world")
        ("Hello world", [])
    """
    # Find all potential image path matches
    matches = IMAGE_PATH_PATTERN.findall(message)

    if not matches:
        return message, []

    valid_paths = []
    seen_paths = set()  # Avoid duplicates

    for match in matches:
        # Resolve to absolute path
        try:
            path = Path(match).expanduser().resolve()

            # Skip if we've already processed this path
            path_str = str(path)
            if path_str in seen_paths:
                continue

            # Validate: must exist and be a file
            if (
                path.exists()
                and path.is_file()
                and path.suffix.lower() in IMAGE_EXTENSIONS
            ):
                valid_paths.append(path_str)
                seen_paths.add(path_str)
        except (OSError, ValueError):
            # Invalid path, skip
            continue

    return message, valid_paths


def validate_image_path(path: str) -> tuple[bool, str]:
    """Validate a single image path for existence and file type.

    Args:
        path: File path to validate (can be relative or absolute)

    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, "")
        If invalid: (False, "descriptive error message")

    Example:
        >>> validate_image_path("screenshot.png")
        (True, "")

        >>> validate_image_path("missing.png")
        (False, "File not found: missing.png")

        >>> validate_image_path("folder")
        (False, "Path is a directory, not a file: folder")
    """
    try:
        # Resolve path
        resolved = Path(path).expanduser().resolve()

        # Check existence
        if not resolved.exists():
            return False, f"File not found: {path}"

        # Check if it's a file (not directory)
        if not resolved.is_file():
            return False, f"Path is a directory, not a file: {path}"

        # Check extension
        if resolved.suffix.lower() not in IMAGE_EXTENSIONS:
            return (
                False,
                f"Invalid image extension: {resolved.suffix} (supported: {', '.join(sorted(IMAGE_EXTENSIONS))})",
            )

        return True, ""

    except (OSError, ValueError) as e:
        return False, f"Invalid path: {e}"


def format_message_with_indicators(message: str, image_paths: list[str]) -> str:
    """Replace image paths in message with visual indicators.

    Args:
        message: Original message text
        image_paths: List of image paths to replace

    Returns:
        Message with image paths replaced by indicators like "🖼️ [filename]"

    Example:
        >>> format_message_with_indicators(
        ...     "Check screenshot.png and logo.jpg",
        ...     ["/path/to/screenshot.png", "/path/to/logo.jpg"]
        ... )
        "Check 🖼️ [screenshot.png] and 🖼️ [logo.jpg]"
    """
    result = message

    for path in image_paths:
        filename = Path(path).name
        # Replace both the full path and just the filename
        result = result.replace(path, f"🖼️ [{filename}]")
        result = result.replace(filename, f"🖼️ [{filename}]")

    return result
