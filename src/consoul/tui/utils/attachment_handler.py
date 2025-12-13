"""Attachment handling utilities for TUI.

Provides helper functions for processing file and image attachments,
reducing complexity in the main app event handlers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.config import ConsoulConfig
    from consoul.tui.widgets.input_area import AttachedFile

logger = logging.getLogger(__name__)

__all__ = [
    "process_image_attachments",
    "process_text_attachments",
    "validate_attachment_size",
]


def process_text_attachments(
    attached_files: list[AttachedFile],
    user_message: str,
    max_size_kb: int = 10,
) -> str:
    """Process text file attachments and prepend their contents to the message.

    Args:
        attached_files: List of attached files from InputArea
        user_message: Original user message
        max_size_kb: Maximum file size in KB (default: 10KB)

    Returns:
        Message with file contents prepended, or original message if no text files
    """
    # Filter text files
    text_files = [f for f in attached_files if f.type in {"code", "document", "data"}]

    if not text_files:
        return user_message

    text_content_parts = []
    max_bytes = max_size_kb * 1024

    for file in text_files:
        try:
            path_obj = Path(file.path)

            # Check file size
            if path_obj.stat().st_size > max_bytes:
                logger.warning(
                    f"Skipping large file {path_obj.name} "
                    f"({path_obj.stat().st_size} bytes, max: {max_bytes})"
                )
                continue

            # Read file content
            content = path_obj.read_text(encoding="utf-8")
            text_content_parts.append(
                f"--- {path_obj.name} ---\n{content}\n--- End of {path_obj.name} ---"
            )

        except Exception as e:
            logger.error(f"Failed to read file {file.path}: {e}")
            continue

    # Prepend file contents to message if any were read
    if text_content_parts:
        return "\n\n".join(text_content_parts) + "\n\n" + user_message

    return user_message


def process_image_attachments(
    attached_files: list[AttachedFile],
    user_message: str,
    config: ConsoulConfig | None,
) -> list[str]:
    """Process image attachments and combine with auto-detected paths.

    Args:
        attached_files: List of attached files from InputArea
        user_message: User message to scan for image paths
        config: Consoul configuration (for auto-detection settings)

    Returns:
        Deduplicated list of all image paths (attached + auto-detected)
    """
    from consoul.tui.utils.image_parser import extract_image_paths

    # Get explicitly attached images
    attached_images = [f.path for f in attached_files if f.type == "image"]

    # Check if auto-detection is enabled
    auto_detect_enabled = False
    if config and config.tools:
        image_tool_config = config.tools.image_analysis
        auto_detect_enabled = getattr(
            image_tool_config, "auto_detect_in_messages", False
        )

    # Extract image paths from message if auto-detection enabled
    auto_detected_paths: list[str] = []
    if auto_detect_enabled:
        _original_message, auto_detected_paths = extract_image_paths(user_message)

    # Combine and deduplicate
    all_image_paths = list(set(attached_images + auto_detected_paths))

    # Debug logging
    logger.info(
        f"[IMAGE_DETECTION] Auto-detect enabled: {auto_detect_enabled}, "
        f"Attached images: {len(attached_images)}, "
        f"Auto-detected: {len(auto_detected_paths)}, "
        f"Total (deduplicated): {len(all_image_paths)}"
    )
    if all_image_paths:
        logger.info(f"[IMAGE_DETECTION] Image paths: {all_image_paths}")

    return all_image_paths


def validate_attachment_size(file_path: str | Path, max_size_kb: int = 10) -> bool:
    """Validate that an attachment is within size limits.

    Args:
        file_path: Path to the file
        max_size_kb: Maximum allowed size in KB

    Returns:
        True if file is within limits, False otherwise
    """
    try:
        path_obj = Path(file_path)
        max_bytes = max_size_kb * 1024
        file_size = path_obj.stat().st_size

        if file_size > max_bytes:
            logger.warning(
                f"File {path_obj.name} exceeds size limit: "
                f"{file_size} bytes (max: {max_bytes})"
            )
            return False

        return True

    except Exception as e:
        logger.error(f"Failed to validate file {file_path}: {e}")
        return False
