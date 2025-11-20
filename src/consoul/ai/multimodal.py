"""Multimodal message formatting for vision-capable LLM providers.

This module provides provider-specific message formatting utilities for
vision/multimodal AI capabilities. It converts base64-encoded images into
the correct message structure for Anthropic Claude, OpenAI GPT-4V, Google Gemini,
and Ollama vision models (qwen3-vl, llava, bakllava).

Each provider has different requirements for multimodal message formatting:
- **Anthropic**: Content blocks with type="image", source={type="base64", ...}
- **OpenAI**: Content array with type="image_url", image_url={url: "data:..."}
- **Google**: Content array with type="image", base64="...", mime_type="..."
- **Ollama**: Content array with type="image", url="data:..."

Usage:
    >>> from consoul.ai.multimodal import format_vision_message
    >>> from consoul.config.models import Provider
    >>>
    >>> # Get images from analyze_images tool
    >>> images = [
    ...     {"path": "/path/to/image.png", "data": "base64...", "mime_type": "image/png"}
    ... ]
    >>>
    >>> # Format for specific provider
    >>> content = format_vision_message(
    ...     Provider.ANTHROPIC,
    ...     "What's in this image?",
    ...     images
    ... )
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from consoul.config.models import Provider


def _detect_mime_type(path: str, mime_type: str | None = None) -> str:
    """Detect MIME type from path or explicit mime_type.

    Args:
        path: File path (used for extension-based detection)
        mime_type: Explicit MIME type (takes precedence)

    Returns:
        MIME type string (e.g., "image/png", "image/jpeg")

    Raises:
        ValueError: If MIME type cannot be determined
    """
    if mime_type:
        return mime_type

    # Fallback to extension-based detection
    import mimetypes

    detected, _ = mimetypes.guess_type(path)
    if detected and detected.startswith("image/"):
        return detected

    raise ValueError(
        f"Could not detect MIME type for {path}. "
        "Ensure file has a valid image extension or provide mime_type explicitly."
    )


def format_anthropic_vision(query: str, images: list[dict[str, Any]]) -> HumanMessage:
    """Format vision message for Anthropic Claude 3+ models.

    Anthropic uses content blocks with explicit type fields and structured
    image sources with base64 data.

    Args:
        query: Natural language question or instruction about the images
        images: List of image dicts with keys: path, data (base64), mime_type

    Returns:
        HumanMessage with content blocks ready for LangChain ChatAnthropic

    Example:
        >>> images = [{"path": "img.png", "data": "iVBORw0...", "mime_type": "image/png"}]
        >>> message = format_anthropic_vision("Describe this", images)
        >>> isinstance(message, HumanMessage)
        True
        >>> message.content[0]
        {"type": "text", "text": "Describe this"}
        >>> message.content[1]
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": "iVBORw0..."
            }
        }
    """
    content: list[str | dict[str, Any]] = [{"type": "text", "text": query}]

    for img in images:
        mime_type = _detect_mime_type(img["path"], img.get("mime_type"))
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": img["data"],
                },
            }
        )

    return HumanMessage(content=content)


def format_openai_vision(query: str, images: list[dict[str, Any]]) -> HumanMessage:
    """Format vision message for OpenAI GPT-4V models.

    OpenAI uses data URIs with base64-encoded images in the image_url field.

    Args:
        query: Natural language question or instruction about the images
        images: List of image dicts with keys: path, data (base64), mime_type

    Returns:
        HumanMessage with content blocks ready for LangChain ChatOpenAI

    Example:
        >>> images = [{"path": "img.jpg", "data": "/9j/4AA...", "mime_type": "image/jpeg"}]
        >>> message = format_openai_vision("Analyze this", images)
        >>> isinstance(message, HumanMessage)
        True
        >>> message.content[0]
        {"type": "text", "text": "Analyze this"}
        >>> message.content[1]
        {
            "type": "image_url",
            "image_url": {"url": "data:image/jpeg;base64,/9j/4AA..."}
        }
    """
    content: list[str | dict[str, Any]] = [{"type": "text", "text": query}]

    for img in images:
        mime_type = _detect_mime_type(img["path"], img.get("mime_type"))
        data_uri = f"data:{mime_type};base64,{img['data']}"
        content.append({"type": "image_url", "image_url": {"url": data_uri}})

    return HumanMessage(content=content)


def format_google_vision(query: str, images: list[dict[str, Any]]) -> HumanMessage:
    """Format vision message for Google Gemini models.

    Google Gemini uses inline base64 data with explicit MIME type fields.

    Args:
        query: Natural language question or instruction about the images
        images: List of image dicts with keys: path, data (base64), mime_type

    Returns:
        HumanMessage with content blocks ready for LangChain ChatGoogleGenerativeAI

    Example:
        >>> images = [{"path": "img.webp", "data": "UklGR...", "mime_type": "image/webp"}]
        >>> message = format_google_vision("What is this?", images)
        >>> isinstance(message, HumanMessage)
        True
        >>> message.content[0]
        {"type": "text", "text": "What is this?"}
        >>> message.content[1]
        {
            "type": "image",
            "base64": "UklGR...",
            "mime_type": "image/webp"
        }
    """
    content: list[str | dict[str, Any]] = [{"type": "text", "text": query}]

    for img in images:
        mime_type = _detect_mime_type(img["path"], img.get("mime_type"))
        content.append({"type": "image", "base64": img["data"], "mime_type": mime_type})

    return HumanMessage(content=content)


def format_ollama_vision(query: str, images: list[dict[str, Any]]) -> HumanMessage:
    """Format vision message for Ollama vision models (qwen3-vl, llava, bakllava).

    Ollama uses data URIs similar to OpenAI but with a different content structure.

    Args:
        query: Natural language question or instruction about the images
        images: List of image dicts with keys: path, data (base64), mime_type

    Returns:
        HumanMessage with content blocks ready for LangChain ChatOllama

    Example:
        >>> images = [{"path": "img.png", "data": "iVBORw0...", "mime_type": "image/png"}]
        >>> message = format_ollama_vision("Describe", images)
        >>> isinstance(message, HumanMessage)
        True
        >>> message.content[0]
        {"type": "text", "text": "Describe"}
        >>> message.content[1]
        {
            "type": "image",
            "url": "data:image/png;base64,iVBORw0..."
        }

    Note:
        This format works with qwen3-vl, llava, bakllava, and other Ollama vision models.
    """
    content: list[str | dict[str, Any]] = [{"type": "text", "text": query}]

    for img in images:
        mime_type = _detect_mime_type(img["path"], img.get("mime_type"))
        data_uri = f"data:{mime_type};base64,{img['data']}"
        content.append({"type": "image", "url": data_uri})

    return HumanMessage(content=content)


def format_vision_message(
    provider: Provider,
    query: str,
    images: list[dict[str, Any]],
) -> HumanMessage:
    """Auto-select provider-specific vision message formatting.

    This is the main entry point for formatting multimodal messages. It
    automatically dispatches to the correct provider-specific formatter.

    Args:
        provider: AI provider enum (ANTHROPIC, OPENAI, GOOGLE, OLLAMA)
        query: Natural language question or instruction about the images
        images: List of image dicts from analyze_images tool output
                Each dict should have: path, data (base64), mime_type

    Returns:
        HumanMessage object ready for LangChain chat providers

    Raises:
        ValueError: If provider doesn't support vision capabilities

    Example:
        >>> from consoul.config.models import Provider
        >>> images = [
        ...     {"path": "screenshot.png", "data": "iVBORw0...", "mime_type": "image/png"}
        ... ]
        >>> message = format_vision_message(
        ...     Provider.ANTHROPIC,
        ...     "What error is shown?",
        ...     images
        ... )
        >>> # Pass message directly to LangChain ChatAnthropic, ChatOpenAI, etc.
        >>> response = chat_model.invoke([message])
    """
    formatters = {
        Provider.ANTHROPIC: format_anthropic_vision,
        Provider.OPENAI: format_openai_vision,
        Provider.GOOGLE: format_google_vision,
        Provider.OLLAMA: format_ollama_vision,
    }

    if provider not in formatters:
        supported = ", ".join(p.value for p in formatters)
        raise ValueError(
            f"Provider {provider.value} does not support vision capabilities. "
            f"Supported providers: {supported}"
        )

    return formatters[provider](query, images)


__all__ = [
    "format_anthropic_vision",
    "format_google_vision",
    "format_ollama_vision",
    "format_openai_vision",
    "format_vision_message",
]
