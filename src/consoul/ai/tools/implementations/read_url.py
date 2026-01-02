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

import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from langchain_core.tools import tool

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.config.models import ReadUrlToolConfig

# Cloud metadata endpoints to block
METADATA_IPS: frozenset[str] = frozenset({"169.254.169.254", "fd00:ec2::254"})

# Blocked hostnames (checked before DNS resolution)
BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
        "kubernetes.default.svc",
    }
)

# Maximum redirects to follow
MAX_REDIRECTS: int = 5

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


def _resolve_hostname(hostname: str, dns_timeout: float) -> list[str]:
    """Resolve hostname to IP addresses via socket.getaddrinfo.

    Handles IP literals directly without DNS resolution.

    Args:
        hostname: Hostname or IP literal to resolve
        dns_timeout: Timeout for DNS resolution in seconds

    Returns:
        List of resolved IP address strings

    Raises:
        ToolExecutionError: If DNS resolution fails or times out
    """
    # Handle IP literals directly (no DNS resolution needed)
    try:
        ip = ipaddress.ip_address(hostname)
        return [str(ip)]
    except ValueError:
        pass  # Not an IP literal, proceed with DNS resolution

    # Resolve hostname with timeout
    previous_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(dns_timeout)
        results = socket.getaddrinfo(
            hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
        )
        # Extract unique IP addresses
        ips: list[str] = []
        seen: set[str] = set()
        for result in results:
            addr = result[4][0]
            if isinstance(addr, str) and addr not in seen:
                ips.append(addr)
                seen.add(addr)
        if not ips:
            raise ToolExecutionError(
                f"DNS resolution returned no IP addresses for {hostname}"
            )
        return ips
    except socket.gaierror as e:
        raise ToolExecutionError(f"DNS resolution failed for {hostname}: {e}") from e
    except TimeoutError as e:
        raise ToolExecutionError(f"DNS resolution timed out for {hostname}") from e
    finally:
        socket.setdefaulttimeout(previous_timeout)


def _is_ip_private(ip_str: str) -> tuple[bool, str]:
    """Check if an IP address is private/blocked.

    Uses the ipaddress module for comprehensive IP validation including:
    - Loopback addresses (127.0.0.0/8, ::1)
    - Private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Link-local (169.254.0.0/16, fe80::/10)
    - Reserved, multicast, and unspecified addresses
    - Cloud metadata endpoints
    - IPv6-mapped IPv4 addresses

    Args:
        ip_str: IP address string to check

    Returns:
        Tuple of (is_private, reason). If is_private is False, reason is empty.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True, f"Invalid IP address: {ip_str}"

    # Handle IPv6-mapped IPv4 addresses first (::ffff:x.x.x.x)
    # Must check before other IPv6 checks since these map to IPv4 space
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return _is_ip_private(str(ip.ipv4_mapped))

    # Check cloud metadata IPs explicitly
    if ip_str in METADATA_IPS:
        return True, "Cloud metadata endpoint"

    # Check loopback
    if ip.is_loopback:
        return True, "Loopback address"

    # Check link-local
    if ip.is_link_local:
        return True, "Link-local address"

    # Check multicast
    if ip.is_multicast:
        return True, "Multicast address"

    # Check unspecified (0.0.0.0, ::)
    if ip.is_unspecified:
        return True, "Unspecified address"

    # Check private ranges
    if ip.is_private:
        return True, "Private network address"

    # Check reserved last (most general catch-all)
    # Skip for addresses already handled above
    if ip.is_reserved:
        return True, "Reserved address"

    return False, ""


def _validate_url(url: str) -> list[str]:
    """Validate URL is safe to fetch (prevent SSRF attacks).

    Performs DNS resolution BEFORE any network request to validate that
    the resolved IPs are not private/internal. This prevents DNS rebinding
    attacks where a public hostname resolves to a private IP.

    Args:
        url: URL to validate

    Returns:
        List of resolved IP addresses (for use in redirect validation)

    Raises:
        ToolExecutionError: If URL is invalid, resolves to private IPs, or is unsafe
    """
    config = get_read_url_config()

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ToolExecutionError(f"Invalid URL format: {e}") from e

    # Must be HTTP(S)
    if parsed.scheme not in ("http", "https"):
        raise ToolExecutionError(
            f"Only HTTP(S) URLs are supported, got scheme: {parsed.scheme}"
        )

    # Must have hostname
    hostname = parsed.hostname
    if not hostname:
        raise ToolExecutionError("URL must have a hostname")

    hostname_lower = hostname.lower()

    # Check blocked hostnames (before DNS to fail fast)
    if hostname_lower in BLOCKED_HOSTNAMES and not config.allow_private_networks:
        raise ToolExecutionError(
            f"Blocked hostname: {hostname_lower} (security restriction)"
        )

    # Resolve hostname to IP addresses
    resolved_ips = _resolve_hostname(hostname_lower, config.dns_timeout)

    # Skip IP validation if allow_private_networks is enabled
    if config.allow_private_networks:
        logger.warning(
            f"SSRF protection disabled for {url} (allow_private_networks=True)"
        )
        return resolved_ips

    # Validate ALL resolved IPs - reject if ANY is private
    for ip_str in resolved_ips:
        is_private, reason = _is_ip_private(ip_str)
        if is_private:
            raise ToolExecutionError(
                f"Cannot fetch URL: {hostname} resolves to {ip_str} ({reason}). "
                "Private/internal IPs are blocked for security."
            )

    logger.debug(f"URL validated: {url} -> {resolved_ips}")
    return resolved_ips


def _read_with_jina(url: str, api_key: str | None, timeout: int) -> str:
    """Read URL using Jina AI Reader API with redirect validation.

    Handles redirects manually to validate each redirect destination
    for SSRF protection.

    Args:
        url: URL to read
        api_key: Optional Jina API key for higher rate limits
        timeout: Request timeout in seconds

    Returns:
        Markdown content from the URL

    Raises:
        ToolExecutionError: If Jina fails, is rate limited, or redirect is unsafe
    """
    try:
        # Build Jina Reader URL
        current_url = f"https://r.jina.ai/{url}"

        # Add authorization header if API key provided
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        for redirect_count in range(MAX_REDIRECTS + 1):
            logger.debug(f"Fetching URL via Jina Reader: {current_url}")

            response = requests.get(
                current_url,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,  # Handle redirects manually for SSRF protection
            )

            # Check for redirects
            if response.status_code in (301, 302, 303, 307, 308):
                if redirect_count >= MAX_REDIRECTS:
                    raise ToolExecutionError(
                        f"Too many redirects (max: {MAX_REDIRECTS})"
                    )

                redirect_url = response.headers.get("Location")
                if not redirect_url:
                    raise ToolExecutionError("Redirect without Location header")

                # Handle relative redirects
                if not redirect_url.startswith(("http://", "https://")):
                    redirect_url = urljoin(current_url, redirect_url)

                # Validate the redirect destination
                logger.debug(f"Validating redirect to: {redirect_url}")
                _validate_url(redirect_url)

                current_url = redirect_url
                continue

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

        # Should not reach here, but just in case
        raise ToolExecutionError("Redirect loop detected")

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
    """Read URL using trafilatura (local processing) with redirect validation.

    Fetches HTML ourselves with manual redirect handling to validate each
    redirect destination for SSRF protection, then passes HTML to trafilatura
    for content extraction.

    Args:
        url: URL to read
        timeout: Request timeout in seconds

    Returns:
        Markdown content from the URL

    Raises:
        ToolExecutionError: If trafilatura fails or redirect is unsafe
    """
    try:
        logger.debug(f"Fetching URL via trafilatura: {url}")
        current_url = url

        # Fetch with redirect validation
        for redirect_count in range(MAX_REDIRECTS + 1):
            response = requests.get(
                current_url,
                timeout=timeout,
                allow_redirects=False,  # Handle redirects manually for SSRF protection
                headers={"User-Agent": "Mozilla/5.0 (compatible; Consoul/1.0)"},
            )

            # Check for redirects
            if response.status_code in (301, 302, 303, 307, 308):
                if redirect_count >= MAX_REDIRECTS:
                    raise ToolExecutionError(
                        f"Too many redirects (max: {MAX_REDIRECTS})"
                    )

                redirect_url = response.headers.get("Location")
                if not redirect_url:
                    raise ToolExecutionError("Redirect without Location header")

                # Handle relative redirects
                if not redirect_url.startswith(("http://", "https://")):
                    redirect_url = urljoin(current_url, redirect_url)

                # Validate redirect destination
                logger.debug(f"Validating redirect to: {redirect_url}")
                _validate_url(redirect_url)

                current_url = redirect_url
                continue

            if response.status_code != 200:
                raise ToolExecutionError(
                    f"HTTP {response.status_code}: Failed to download URL"
                )

            downloaded = response.text
            break
        else:
            raise ToolExecutionError("Redirect loop detected")

        if not downloaded:
            raise ToolExecutionError(
                "Failed to download URL (network error or invalid URL)"
            )

        # Extract content as markdown using trafilatura
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


@tool
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
