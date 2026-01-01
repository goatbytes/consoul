"""SSRF protection and URL validation for webhooks.

Implements security controls to prevent Server-Side Request Forgery (SSRF)
attacks when delivering webhooks to user-specified URLs.

Security Controls:
    - HTTPS required (configurable localhost for development)
    - Private IP range blocking (RFC 1918, RFC 4193, link-local)
    - Cloud metadata endpoint blocking (169.254.169.254)
    - Redirect limit enforcement (max 3, same-host only)
    - DNS rebinding protection (resolve at enqueue + connect)
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

__all__ = [
    "URLValidationError",
    "ValidatedURL",
    "WebhookURLValidator",
]


class URLValidationError(Exception):
    """Raised when URL validation fails."""

    def __init__(self, reason: str, code: str = "invalid_url") -> None:
        self.reason = reason
        self.code = code
        super().__init__(reason)


@dataclass
class ValidatedURL:
    """Result of URL validation.

    Attributes:
        url: The validated URL
        host: Extracted hostname
        resolved_ips: IP addresses the hostname resolves to
    """

    url: str
    host: str
    resolved_ips: list[str]


# Private IPv4 ranges (RFC 1918 + link-local + loopback)
PRIVATE_IPV4_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
]

# Private IPv6 ranges (RFC 4193 + link-local + loopback)
PRIVATE_IPV6_NETWORKS = [
    ipaddress.ip_network("fc00::/7"),  # Unique local addresses
    ipaddress.ip_network("fe80::/10"),  # Link-local
    ipaddress.ip_network("::1/128"),  # Loopback
]

# Cloud metadata endpoints to block
METADATA_IPS = [
    "169.254.169.254",  # AWS, GCP, Azure
    "fd00:ec2::254",  # AWS IPv6
    "metadata.google.internal",
]

# Dangerous hostnames
BLOCKED_HOSTNAMES = [
    "localhost",
    "metadata.google.internal",
    "metadata",
    "kubernetes.default.svc",
]


class WebhookURLValidator:
    """Validates webhook URLs for security.

    Prevents SSRF attacks by validating URLs before webhook delivery.

    Example:
        >>> validator = WebhookURLValidator(allow_localhost=False)
        >>> result = validator.validate("https://example.com/webhook")
        >>> result.host
        'example.com'

        >>> validator.validate("http://localhost/hook")
        URLValidationError: URL must use HTTPS

        >>> validator.validate("https://192.168.1.1/hook")
        URLValidationError: Private IP addresses are not allowed
    """

    def __init__(
        self,
        allow_localhost: bool = False,
        allow_http: bool = False,
        max_redirects: int = 3,
        dns_timeout: float = 5.0,
    ) -> None:
        """Initialize URL validator.

        Args:
            allow_localhost: Allow localhost URLs (development only)
            allow_http: Allow HTTP URLs (insecure, not recommended)
            max_redirects: Maximum number of redirects to follow
            dns_timeout: Timeout for DNS resolution in seconds
        """
        self.allow_localhost = allow_localhost
        self.allow_http = allow_http
        self.max_redirects = max_redirects
        self.dns_timeout = dns_timeout

    def validate(self, url: str) -> ValidatedURL:
        """Validate a webhook URL.

        Args:
            url: The URL to validate

        Returns:
            ValidatedURL with resolved information

        Raises:
            URLValidationError: If URL fails validation
        """
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise URLValidationError(f"Invalid URL format: {e}") from e

        # Check scheme
        if not self.allow_http and parsed.scheme != "https":
            raise URLValidationError(
                "URL must use HTTPS",
                code="https_required",
            )

        if parsed.scheme not in ("http", "https"):
            raise URLValidationError(
                f"Invalid scheme: {parsed.scheme}",
                code="invalid_scheme",
            )

        # Check host exists
        if not parsed.hostname:
            raise URLValidationError("URL must include a hostname")

        hostname = parsed.hostname.lower()

        # Check for blocked hostnames
        if hostname in BLOCKED_HOSTNAMES and not (
            self.allow_localhost and hostname == "localhost"
        ):
            raise URLValidationError(
                f"Hostname not allowed: {hostname}",
                code="blocked_hostname",
            )

        # Resolve DNS and validate IPs
        resolved_ips = self._resolve_host(hostname)

        # Validate each resolved IP
        for ip_str in resolved_ips:
            self._validate_ip(ip_str, hostname)

        return ValidatedURL(
            url=url,
            host=hostname,
            resolved_ips=resolved_ips,
        )

    def _resolve_host(self, hostname: str) -> list[str]:
        """Resolve hostname to IP addresses.

        Args:
            hostname: The hostname to resolve

        Returns:
            List of resolved IP addresses

        Raises:
            URLValidationError: If DNS resolution fails
        """
        # Handle IP addresses directly
        try:
            ip = ipaddress.ip_address(hostname)
            return [str(ip)]
        except ValueError:
            pass  # Not an IP, continue with DNS resolution

        # Resolve hostname with timeout (restore previous timeout after)
        previous_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(self.dns_timeout)
            results = socket.getaddrinfo(
                hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
            # Extract IP addresses (result[4][0] is the IP string)
            ips: list[str] = []
            seen: set[str] = set()
            for result in results:
                addr = result[4][0]
                if isinstance(addr, str) and addr not in seen:
                    ips.append(addr)
                    seen.add(addr)
            if not ips:
                raise URLValidationError(
                    f"No IP addresses found for {hostname}",
                    code="dns_resolution_failed",
                )
            return ips
        except socket.gaierror as e:
            raise URLValidationError(
                f"DNS resolution failed for {hostname}: {e}",
                code="dns_resolution_failed",
            ) from e
        except TimeoutError as e:
            raise URLValidationError(
                f"DNS resolution timed out for {hostname}",
                code="dns_timeout",
            ) from e
        finally:
            # Restore previous timeout to avoid affecting other network operations
            socket.setdefaulttimeout(previous_timeout)

    def _validate_ip(self, ip_str: str, hostname: str) -> None:
        """Validate an IP address is not private/blocked.

        Args:
            ip_str: The IP address string
            hostname: The original hostname (for error messages)

        Raises:
            URLValidationError: If IP is not allowed
        """
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError as e:
            raise URLValidationError(f"Invalid IP address: {ip_str}") from e

        # Check metadata IPs
        if ip_str in METADATA_IPS:
            raise URLValidationError(
                "Cloud metadata endpoints are blocked",
                code="metadata_blocked",
            )

        # Check localhost
        if ip.is_loopback:
            if not self.allow_localhost:
                raise URLValidationError(
                    "Localhost addresses are not allowed",
                    code="localhost_blocked",
                )
            return  # Localhost allowed in dev mode

        # Check private ranges
        if isinstance(ip, ipaddress.IPv4Address):
            for network in PRIVATE_IPV4_NETWORKS:
                if ip in network:
                    raise URLValidationError(
                        f"Private IP addresses are not allowed: {ip_str}",
                        code="private_ip_blocked",
                    )
        else:  # IPv6
            for network in PRIVATE_IPV6_NETWORKS:
                if ip in network:
                    raise URLValidationError(
                        f"Private IPv6 addresses are not allowed: {ip_str}",
                        code="private_ip_blocked",
                    )

        # Check link-local
        if ip.is_link_local:
            raise URLValidationError(
                f"Link-local addresses are not allowed: {ip_str}",
                code="link_local_blocked",
            )

        # Check reserved ranges
        if ip.is_reserved:
            raise URLValidationError(
                f"Reserved IP addresses are not allowed: {ip_str}",
                code="reserved_ip_blocked",
            )

    def validate_redirect(
        self,
        original_url: str,
        redirect_url: str,
        redirect_count: int,
    ) -> ValidatedURL:
        """Validate a redirect URL.

        Ensures redirects stay on the same host and don't exceed limits.

        Args:
            original_url: The original webhook URL
            redirect_url: The redirect target URL
            redirect_count: Current redirect count

        Returns:
            ValidatedURL if redirect is allowed

        Raises:
            URLValidationError: If redirect is not allowed
        """
        if redirect_count >= self.max_redirects:
            raise URLValidationError(
                f"Too many redirects (max: {self.max_redirects})",
                code="too_many_redirects",
            )

        # Parse both URLs
        original_parsed = urlparse(original_url)
        redirect_parsed = urlparse(redirect_url)

        # Check same-host redirect
        if original_parsed.hostname != redirect_parsed.hostname:
            raise URLValidationError(
                f"Cross-host redirects not allowed: {original_parsed.hostname} -> {redirect_parsed.hostname}",
                code="cross_host_redirect",
            )

        # Validate the redirect URL fully
        return self.validate(redirect_url)


def is_safe_url(url: str, allow_localhost: bool = False) -> bool:
    """Quick check if a URL is safe for webhook delivery.

    Args:
        url: The URL to check
        allow_localhost: Allow localhost URLs

    Returns:
        True if URL passes basic safety checks
    """
    try:
        validator = WebhookURLValidator(allow_localhost=allow_localhost)
        validator.validate(url)
        return True
    except URLValidationError:
        return False
