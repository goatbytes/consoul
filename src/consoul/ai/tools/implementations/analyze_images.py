"""Image analysis tool with security controls and validation.

Provides secure image analysis with:
- Base64 encoding for API transmission
- MIME type detection
- File size validation
- Extension filtering
- Magic byte verification (prevents extension spoofing)
- Path security validation
- Support for multiple images per query

Note:
    This tool is classified as RiskLevel.CAUTION since it reads user files
    and sends them to external APIs. Requires user approval workflow.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from consoul.config.models import ImageAnalysisToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: ImageAnalysisToolConfig | None = None


def set_analyze_images_config(config: ImageAnalysisToolConfig) -> None:
    """Set the module-level config for image analysis tool.

    This should be called by the ToolRegistry when registering analyze_images
    to inject the profile's configured settings.

    Args:
        config: ImageAnalysisToolConfig from the active profile's ToolConfig.image_analysis
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_analyze_images_config() -> ImageAnalysisToolConfig:
    """Get the current image analysis tool config.

    Returns:
        The configured ImageAnalysisToolConfig, or a new default instance if not set.
    """
    return _TOOL_CONFIG if _TOOL_CONFIG is not None else ImageAnalysisToolConfig()


def _detect_mime_type(path: Path) -> str:
    """Detect MIME type for image file.

    Args:
        path: Path to image file

    Returns:
        MIME type string (e.g., "image/png", "image/jpeg")

    Raises:
        ValueError: If MIME type cannot be detected or is not an image type
    """
    mime_type, _ = mimetypes.guess_type(str(path))

    if mime_type is None:
        raise ValueError(
            f"Could not detect MIME type for {path.name}. "
            f"Ensure file has a valid image extension."
        )

    if not mime_type.startswith("image/"):
        raise ValueError(f"File {path.name} is not an image (MIME type: {mime_type})")

    return mime_type


def _validate_path(file_path: str, config: ImageAnalysisToolConfig) -> Path:
    """Validate file path for security and accessibility.

    Args:
        file_path: Path to image file to read
        config: ImageAnalysisToolConfig with security settings

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path is invalid, blocked, or inaccessible
    """
    # Check for path traversal attempts BEFORE resolving
    if ".." in file_path:
        raise ValueError("Path traversal (..) not allowed for security")

    # Resolve to absolute path (expand ~)
    path = Path(file_path).expanduser().resolve()

    # Check blocked paths BEFORE checking existence
    # This prevents probing for file existence in blocked locations
    path_str = str(path)
    for blocked in config.blocked_paths:
        # Resolve blocked path too for comparison (expand ~)
        blocked_resolved = str(Path(blocked).expanduser().resolve())
        if path_str.startswith(blocked) or path_str.startswith(blocked_resolved):
            raise ValueError(
                f"Reading from {blocked} is not allowed for security reasons"
            )

    # Check if file exists
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")

    # Check if it's a directory
    if path.is_dir():
        raise ValueError(
            f"Cannot analyze directory: {file_path}. Specify an image file path instead."
        )

    return path


def _validate_extension(path: Path, config: ImageAnalysisToolConfig) -> None:
    """Validate file extension against allowed list.

    Args:
        path: Path to file to check
        config: ImageAnalysisToolConfig with allowed_extensions list

    Raises:
        ValueError: If extension is not in allowed list
    """
    suffix = path.suffix.lower()
    # Normalize config extensions to lowercase for case-insensitive comparison
    allowed_lower = [ext.lower() for ext in config.allowed_extensions]

    if suffix not in allowed_lower:
        raise ValueError(
            f"File extension '{suffix or '(none)'}' not allowed. "
            f"Allowed extensions: {', '.join(config.allowed_extensions)}"
        )


def _validate_file_type(path: Path) -> None:
    """Validate file is actually an image using magic byte verification.

    Uses PIL to verify the file can be opened as a valid image, preventing
    extension spoofing attacks (e.g., malware.exe renamed to malware.png).

    Args:
        path: Path to file to validate

    Raises:
        ValueError: If file is not a valid image
    """
    try:
        from PIL import Image
    except ImportError:
        # PIL not available - skip magic byte validation
        # This is acceptable since we still have extension validation
        return

    try:
        with Image.open(path) as img:
            # Verify the image by trying to load it
            img.verify()
    except Exception as e:
        raise ValueError(f"File {path.name} is not a valid image file: {e}") from e


def _validate_size(path: Path, config: ImageAnalysisToolConfig) -> None:
    """Validate file size is within configured limit.

    Args:
        path: Path to file to check
        config: ImageAnalysisToolConfig with max_image_size_mb limit

    Raises:
        ValueError: If file exceeds size limit
    """
    size_bytes = path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    max_mb = config.max_image_size_mb

    if size_mb > max_mb:
        raise ValueError(
            f"Image {path.name} ({size_mb:.1f} MB) exceeds maximum size of {max_mb} MB"
        )


class AnalyzeImagesInput(BaseModel):
    """Input schema for analyze_images tool."""

    query: str = Field(
        description="Question or instruction about the image(s). "
        "Examples: 'What error is shown?', 'Describe this diagram', "
        "'Is this UI accessible?'"
    )
    image_paths: list[str] = Field(
        description="List of local image file paths to analyze. "
        "Supports: PNG, JPG, JPEG, GIF, WebP, BMP",
        min_length=1,
    )


@tool(args_schema=AnalyzeImagesInput)
def analyze_images(query: str, image_paths: list[str]) -> str:
    """Analyze images using AI vision capabilities.

    This tool enables multimodal image analysis for screenshots, diagrams,
    UI mockups, code screenshots, and other visual content. It validates,
    encodes, and prepares images for vision-capable LLM providers.

    Security features:
    - File size limits prevent large uploads
    - Extension validation ensures only image files
    - Magic byte verification prevents extension spoofing
    - Path traversal protection blocks malicious paths
    - Blocked path enforcement prevents accessing sensitive directories

    The tool uses ImageAnalysisToolConfig from the active profile's
    ToolConfig.image_analysis settings. Call set_analyze_images_config()
    to inject the profile configuration before tool registration.

    Args:
        query: Natural language question or instruction about the images
        image_paths: List of local image file paths (absolute or relative)

    Returns:
        JSON string containing the query and base64-encoded images with metadata.
        Format: {"query": str, "images": [{"path": str, "data": str, "mime_type": str}, ...]}
        The caller (AI agent) will send this to the vision-capable LLM.

    Example:
        >>> analyze_images(
        ...     query="What error is shown in this screenshot?",
        ...     image_paths=["./error_screenshot.png"]
        ... )
        '{"query": "What error is shown...", "images": [{"path": "...", "data": "iVBORw0KG...", "mime_type": "image/png"}]}'

    Note:
        This tool does NOT invoke the LLM directly. It only prepares the images
        for transmission. The actual LLM invocation happens in the caller (registry/agent).
    """
    import json

    # Get config from module-level (set by registry via set_analyze_images_config)
    config = get_analyze_images_config()

    # Validate count
    if len(image_paths) > config.max_images_per_query:
        return (
            f"❌ Maximum {config.max_images_per_query} images allowed per query. "
            f"You provided {len(image_paths)} images."
        )

    # Validate and encode each image
    encoded_images = []
    try:
        for path_str in image_paths:
            # Validate path for security
            path = _validate_path(path_str, config)

            # Validate extension
            _validate_extension(path, config)

            # Validate size (before expensive magic byte check)
            _validate_size(path, config)

            # Validate file type (magic byte check)
            _validate_file_type(path)

            # Detect MIME type
            mime_type = _detect_mime_type(path)

            # Encode to base64
            with open(path, "rb") as f:
                base64_data = base64.b64encode(f.read()).decode("utf-8")

            encoded_images.append(
                {
                    "path": str(path),
                    "data": base64_data,
                    "mime_type": mime_type,
                }
            )

    except ValueError as e:
        # Security validation or other expected errors
        return f"❌ {e}"
    except FileNotFoundError:
        return f"❌ File not found: {path_str}"
    except PermissionError:
        return f"❌ Permission denied: {path_str}"
    except Exception as e:
        # Unexpected errors
        return f"❌ Error processing image: {e}"

    # Return JSON string with query and encoded images
    result = {
        "query": query,
        "images": encoded_images,
    }
    return json.dumps(result)
