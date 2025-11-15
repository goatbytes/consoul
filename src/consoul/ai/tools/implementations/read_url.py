"""Read URL tool using Jina AI Reader with trafilatura fallback.

Converts web pages to LLM-ready markdown with automatic fallback:
- Jina AI Reader (primary) - Best quality, LLM-optimized, 20 RPM free
- trafilatura (fallback) - Local processing, privacy-focused, unlimited

Features:
- Zero configuration (no API key needed for basic usage)
- Security validations (blocks localhost, private IPs)
- Automatic fallback on rate limits or failures
- Optional API key for higher rate limits (500 RPM)

Example:
    >>> from consoul.ai.tools.implementations.read_url import read_url
    >>> # Basic usage (uses Jina Reader, falls back to trafilatura)
    >>> result = read_url.invoke({
    ...     "url": "https://goatbytes.io/about",
    ... })
    >>>
    >>> # Force fallback to trafilatura (local, private)
    >>> result = read_url.invoke({
    ...     "url": "https://example.com",
    ...     "use_fallback": True,
    ... })
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
import trafilatura
from langchain_core.tools import tool

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.config.models import ReadUrlToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: ReadUrlToolConfig | None = None

logger = logging.getLogger(__name__)


def set_read_url_config(config: ReadUrlToolConfig) -> None:
    """Set the module-level config for read_url tool.

    This should be called by the ToolRegistry when registering read_url
    to inject the profile's configured settings.

    Args:
        config: ReadUrlToolConfig from the active profile's ToolConfig.read_url
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_read_url_config() -> ReadUrlToolConfig:
    """Get the current read_url tool config.

    Returns:
        The configured ReadUrlToolConfig, or a new default instance if not set.
    """
    return _TOOL_CONFIG if _TOOL_CONFIG is not None else ReadUrlToolConfig()


def _validate_url(url: str) -> None:
    """Validate URL is safe to fetch (prevent SSRF attacks).

    Args:
        url: URL to validate

    Raises:
        ToolExecutionError: If URL is invalid or unsafe
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ToolExecutionError(f"Invalid URL format: {e}") from e

    # Must be HTTP(S)
    if parsed.scheme not in ("http", "https"):
        raise ToolExecutionError(
            f"Only HTTP(S) URLs are supported, got scheme: {parsed.scheme}"
        )

    # Block localhost
    hostname = parsed.hostname
    if not hostname:
        raise ToolExecutionError("URL must have a hostname")

    hostname_lower = hostname.lower()

    # Block localhost variants
    if hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise ToolExecutionError("Cannot fetch localhost URLs (security restriction)")

    # Block private IP ranges
    if (
        hostname_lower.startswith("192.168.")
        or hostname_lower.startswith("10.")
        or hostname_lower.startswith("172.16.")
        or hostname_lower.startswith("172.17.")
        or hostname_lower.startswith("172.18.")
        or hostname_lower.startswith("172.19.")
        or hostname_lower.startswith("172.20.")
        or hostname_lower.startswith("172.21.")
        or hostname_lower.startswith("172.22.")
        or hostname_lower.startswith("172.23.")
        or hostname_lower.startswith("172.24.")
        or hostname_lower.startswith("172.25.")
        or hostname_lower.startswith("172.26.")
        or hostname_lower.startswith("172.27.")
        or hostname_lower.startswith("172.28.")
        or hostname_lower.startswith("172.29.")
        or hostname_lower.startswith("172.30.")
        or hostname_lower.startswith("172.31.")
    ):
        raise ToolExecutionError(
            "Cannot fetch private network URLs (security restriction)"
        )


def _read_with_jina(url: str, api_key: str | None, timeout: int) -> str:
    """Read URL using Jina AI Reader API.

    Args:
        url: URL to read
        api_key: Optional Jina API key for higher rate limits
        timeout: Request timeout in seconds

    Returns:
        Markdown content from the URL

    Raises:
        ToolExecutionError: If Jina fails or is rate limited
    """
    try:
        # Build Jina Reader URL
        jina_url = f"https://r.jina.ai/{url}"

        # Add authorization header if API key provided
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        logger.debug(f"Fetching URL via Jina Reader: {url}")

        response = requests.get(
            jina_url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )

        # Check for rate limiting
        if response.status_code == 429:
            raise ToolExecutionError(
                "Jina AI Reader rate limit exceeded. "
                "Consider adding JINA_API_KEY for 500 RPM limit, or use fallback."
            )

        # Check for auth errors
        if response.status_code == 401:
            raise ToolExecutionError(
                "Jina AI Reader authentication failed. Check your API key."
            )

        # Check for general errors
        if response.status_code != 200:
            raise ToolExecutionError(
                f"Jina AI Reader returned status {response.status_code}: {response.text[:200]}"
            )

        content: str = str(response.text)

        if not content or len(content.strip()) == 0:
            raise ToolExecutionError("Jina AI Reader returned empty content")

        logger.info(f"Successfully fetched {len(content)} chars from Jina Reader")
        return content

    except ToolExecutionError:
        # Re-raise our own errors
        raise
    except Exception as e:
        # Wrap other exceptions
        logger.warning(f"Jina AI Reader failed for {url}: {e}")
        raise ToolExecutionError(
            f"Jina AI Reader failed: {e}. Consider using fallback."
        ) from e


def _read_with_trafilatura(url: str, timeout: int) -> str:
    """Read URL using trafilatura (local processing).

    Args:
        url: URL to read
        timeout: Request timeout in seconds

    Returns:
        Markdown content from the URL

    Raises:
        ToolExecutionError: If trafilatura fails
    """
    try:
        logger.debug(f"Fetching URL via trafilatura: {url}")

        # Download HTML
        downloaded = trafilatura.fetch_url(url)

        if not downloaded:
            raise ToolExecutionError(
                "Failed to download URL (network error or invalid URL)"
            )

        # Extract content as markdown
        result: str | None = trafilatura.extract(
            downloaded,
            output_format="markdown",
            include_links=True,
            include_images=False,  # Images are just URLs in markdown
        )

        if not result:
            raise ToolExecutionError(
                "Failed to extract content (page may be JavaScript-heavy or empty)"
            )

        logger.info(f"Successfully extracted {len(result)} chars via trafilatura")
        return result

    except ToolExecutionError:
        raise
    except Exception as e:
        logger.error(f"trafilatura failed for {url}: {e}")
        raise ToolExecutionError(
            f"trafilatura extraction failed: {e}. "
            "Page may require JavaScript rendering."
        ) from e


@tool  # type: ignore[misc]
def read_url(
    url: str,
    use_fallback: bool | None = None,
) -> str:
    """Read and convert a web page to LLM-ready markdown.

    Uses Jina AI Reader for best results, with automatic trafilatura fallback.
    Zero configuration needed - works immediately with 20 RPM free tier.

    Args:
        url: URL to read (must be publicly accessible HTTP/HTTPS)
        use_fallback: Force fallback to trafilatura for privacy (default: auto)

    Returns:
        Markdown-formatted content from the URL, truncated to max_length if needed.

    Raises:
        ToolExecutionError: If both Jina and trafilatura fail, or URL is unsafe

    Example:
        >>> # Basic usage (uses Jina, falls back to trafilatura)
        >>> read_url("https://goatbytes.io/about")
        'Title: About GoatBytes.IO\\n\\nMarkdown Content:\\n...'
        >>>
        >>> # Force local processing (privacy-focused)
        >>> read_url("https://example.com", use_fallback=True)
        '# Example Domain\\n\\nThis domain is for use in...'

    Note:
        - Jina Reader: 20 RPM free (no API key), 500 RPM with free API key
        - trafilatura: Unlimited (local), but may fail on JavaScript-heavy sites
        - Security: Blocks localhost and private IPs to prevent SSRF
        - Rate limiting: Jina rate limit triggers automatic fallback
    """
    config = get_read_url_config()

    # Validate URL for security (SSRF prevention)
    _validate_url(url)

    # Determine which backend to use
    content: str

    if use_fallback:
        # User explicitly requested fallback
        logger.info(f"Using trafilatura (forced fallback): {url}")
        content = _read_with_trafilatura(url, config.timeout)
    else:
        # Try Jina first, fallback to trafilatura if enabled
        try:
            logger.info(f"Using Jina AI Reader: {url}")
            content = _read_with_jina(url, config.jina_api_key, config.timeout)
        except ToolExecutionError as e:
            if config.enable_fallback:
                logger.warning(f"Jina failed, falling back to trafilatura: {e}")
                content = _read_with_trafilatura(url, config.timeout)
            else:
                # Fallback disabled, re-raise error
                raise

    # Truncate if needed
    if len(content) > config.max_length:
        logger.warning(
            f"Content truncated from {len(content)} to {config.max_length} chars"
        )
        content = content[: config.max_length] + "\n\n[Content truncated...]"

    return content
