"""Tests for read_url tool SSRF protection.

Tests comprehensive SSRF (Server-Side Request Forgery) validation including:
- DNS resolution to private IPs
- IPv4/IPv6 private address detection
- Cloud metadata endpoint blocking
- Redirect validation
- Configuration options
"""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.ai.tools.implementations.read_url import (
    BLOCKED_HOSTNAMES,
    METADATA_IPS,
    _is_ip_private,
    _resolve_hostname,
    _validate_url,
    get_read_url_config,
    read_url,
    set_read_url_config,
)
from consoul.config.models import ReadUrlToolConfig


class TestReadUrlConfig:
    """Test ReadUrlToolConfig configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ReadUrlToolConfig()
        assert config.allow_private_networks is False
        assert config.dns_timeout == 5.0
        assert config.timeout == 10
        assert config.enable_fallback is True
        assert config.max_length == 50000

    def test_allow_private_networks_config(self) -> None:
        """Test allow_private_networks can be enabled."""
        config = ReadUrlToolConfig(allow_private_networks=True)
        assert config.allow_private_networks is True

    def test_dns_timeout_config(self) -> None:
        """Test dns_timeout configuration."""
        config = ReadUrlToolConfig(dns_timeout=10.0)
        assert config.dns_timeout == 10.0

    def test_set_get_config(self) -> None:
        """Test setting and getting module-level config."""
        custom_config = ReadUrlToolConfig(
            allow_private_networks=True,
            dns_timeout=3.0,
        )
        set_read_url_config(custom_config)

        try:
            retrieved_config = get_read_url_config()
            assert retrieved_config.allow_private_networks is True
            assert retrieved_config.dns_timeout == 3.0
        finally:
            # Reset to default
            set_read_url_config(ReadUrlToolConfig())


class TestIPValidation:
    """Tests for IP address validation."""

    # IPv4 private addresses
    @pytest.mark.parametrize(
        "ip,expected_private",
        [
            # Loopback
            ("127.0.0.1", True),
            ("127.255.255.255", True),
            # Private Class A (10.0.0.0/8)
            ("10.0.0.1", True),
            ("10.255.255.255", True),
            # Private Class B (172.16.0.0/12)
            ("172.16.0.1", True),
            ("172.31.255.255", True),
            ("172.15.0.1", False),  # Just before range
            ("172.32.0.1", False),  # Just after range
            # Private Class C (192.168.0.0/16)
            ("192.168.0.1", True),
            ("192.168.255.255", True),
            # Link-local (169.254.0.0/16)
            ("169.254.0.1", True),
            ("169.254.169.254", True),  # AWS metadata
            # Public IPs
            ("8.8.8.8", False),
            ("93.184.216.34", False),
            ("1.1.1.1", False),
            # Unspecified
            ("0.0.0.0", True),
        ],
    )
    def test_ipv4_private_detection(self, ip: str, expected_private: bool) -> None:
        """Test IPv4 private address detection."""
        is_private, reason = _is_ip_private(ip)
        assert is_private == expected_private, (
            f"{ip}: expected {expected_private}, got {is_private} ({reason})"
        )

    # IPv6 addresses
    @pytest.mark.parametrize(
        "ip,expected_private",
        [
            # Loopback
            ("::1", True),
            # Link-local
            ("fe80::1", True),
            ("fe80::abcd:1234", True),
            # Unique local (fc00::/7)
            ("fc00::1", True),
            ("fd00::1", True),
            # Public IPv6
            ("2001:4860:4860::8888", False),
            ("2606:4700:4700::1111", False),
            # Unspecified
            ("::", True),
        ],
    )
    def test_ipv6_private_detection(self, ip: str, expected_private: bool) -> None:
        """Test IPv6 private address detection."""
        is_private, reason = _is_ip_private(ip)
        assert is_private == expected_private, (
            f"{ip}: expected {expected_private}, got {is_private} ({reason})"
        )

    # IPv6-mapped IPv4 addresses
    @pytest.mark.parametrize(
        "ip,expected_private",
        [
            ("::ffff:127.0.0.1", True),  # Loopback
            ("::ffff:10.0.0.1", True),  # Private
            ("::ffff:192.168.1.1", True),  # Private
            ("::ffff:8.8.8.8", False),  # Public
            ("::ffff:1.1.1.1", False),  # Public
        ],
    )
    def test_ipv6_mapped_ipv4_detection(self, ip: str, expected_private: bool) -> None:
        """Test IPv6-mapped IPv4 address detection."""
        is_private, reason = _is_ip_private(ip)
        assert is_private == expected_private, (
            f"{ip}: expected {expected_private}, got {is_private} ({reason})"
        )

    def test_cloud_metadata_ips(self) -> None:
        """Test that cloud metadata IPs are blocked."""
        for ip in METADATA_IPS:
            is_private, reason = _is_ip_private(ip)
            assert is_private is True, f"Cloud metadata IP {ip} should be blocked"
            assert "metadata" in reason.lower()

    def test_invalid_ip_returns_private(self) -> None:
        """Test that invalid IP strings are treated as private (fail-safe)."""
        is_private, reason = _is_ip_private("not-an-ip")
        assert is_private is True
        assert "Invalid" in reason


class TestDNSResolution:
    """Tests for DNS resolution with mocked socket."""

    @patch("socket.getaddrinfo")
    def test_dns_resolution_success(self, mock_getaddrinfo: MagicMock) -> None:
        """Test successful DNS resolution."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
        ]

        ips = _resolve_hostname("example.com", 5.0)

        assert ips == ["93.184.216.34"]
        mock_getaddrinfo.assert_called_once()

    @patch("socket.getaddrinfo")
    def test_dns_resolution_multiple_ips(self, mock_getaddrinfo: MagicMock) -> None:
        """Test DNS resolution with multiple IPs."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.2.3.4", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("5.6.7.8", 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("2001:db8::1", 0, 0, 0)),
        ]

        ips = _resolve_hostname("multi.example.com", 5.0)

        assert len(ips) == 3
        assert "1.2.3.4" in ips
        assert "5.6.7.8" in ips
        assert "2001:db8::1" in ips

    @patch("socket.getaddrinfo")
    def test_dns_resolution_deduplication(self, mock_getaddrinfo: MagicMock) -> None:
        """Test that duplicate IPs are deduplicated."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.2.3.4", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.2.3.4", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("5.6.7.8", 0)),
        ]

        ips = _resolve_hostname("example.com", 5.0)

        assert len(ips) == 2
        assert ips.count("1.2.3.4") == 1

    @patch("socket.getaddrinfo")
    def test_dns_resolution_failure(self, mock_getaddrinfo: MagicMock) -> None:
        """Test DNS resolution failure."""
        mock_getaddrinfo.side_effect = socket.gaierror(8, "Name resolution failed")

        with pytest.raises(ToolExecutionError, match="DNS resolution failed"):
            _resolve_hostname("nonexistent.invalid", 5.0)

    def test_ip_literal_bypasses_dns(self) -> None:
        """Test that IP literals don't trigger DNS resolution."""
        ips = _resolve_hostname("8.8.8.8", 5.0)
        assert ips == ["8.8.8.8"]

        ips = _resolve_hostname("::1", 5.0)
        assert ips == ["::1"]


class TestURLValidation:
    """Tests for complete URL validation including DNS resolution."""

    @patch("socket.getaddrinfo")
    def test_valid_public_url(self, mock_getaddrinfo: MagicMock) -> None:
        """Test validation of valid public URL passes."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
        ]

        ips = _validate_url("https://example.com/page")

        assert "93.184.216.34" in ips

    def test_private_ip_literal_blocked(self) -> None:
        """Test that private IP literals are blocked."""
        with pytest.raises(ToolExecutionError, match="Private"):
            _validate_url("https://192.168.1.1/admin")

        with pytest.raises(ToolExecutionError, match="Loopback"):
            _validate_url("https://127.0.0.1/")

        with pytest.raises(ToolExecutionError, match="Private"):
            _validate_url("https://10.0.0.1/internal")

    def test_link_local_blocked(self) -> None:
        """Test that link-local IPs are blocked (including AWS metadata)."""
        # 169.254.169.254 is both link-local and cloud metadata - blocked as metadata
        with pytest.raises(ToolExecutionError, match="metadata"):
            _validate_url("http://169.254.169.254/latest/meta-data")

        # Regular link-local IP (not metadata)
        with pytest.raises(ToolExecutionError, match="Link-local"):
            _validate_url("http://169.254.1.1/internal")

    @patch("socket.getaddrinfo")
    def test_dns_resolving_to_private_ip_blocked(
        self, mock_getaddrinfo: MagicMock
    ) -> None:
        """Test that public hostname resolving to private IP is blocked."""
        # evil.com resolves to 127.0.0.1
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0)),
        ]

        with pytest.raises(ToolExecutionError, match=r"resolves to 127\.0\.0\.1"):
            _validate_url("https://evil.com/ssrf")

    @patch("socket.getaddrinfo")
    def test_mixed_public_private_ips_blocked(
        self, mock_getaddrinfo: MagicMock
    ) -> None:
        """Test that ANY private IP in resolution causes rejection."""
        # Hostname resolves to both public and private IPs
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0)),
        ]

        with pytest.raises(ToolExecutionError, match=r"192\.168\.1\.1"):
            _validate_url("https://mixed.example.com/")

    @patch("socket.getaddrinfo")
    def test_allow_private_networks_flag(self, mock_getaddrinfo: MagicMock) -> None:
        """Test that allow_private_networks flag disables protection."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.100", 0)),
        ]

        # Enable private networks
        config = ReadUrlToolConfig(allow_private_networks=True)
        set_read_url_config(config)

        try:
            # Should NOT raise even though IP is private
            ips = _validate_url("https://internal.company.local/docs")
            assert "192.168.1.100" in ips
        finally:
            # Reset to default
            set_read_url_config(ReadUrlToolConfig())

    def test_blocked_hostnames(self) -> None:
        """Test that blocked hostnames are rejected."""
        for hostname in BLOCKED_HOSTNAMES:
            with pytest.raises(ToolExecutionError, match="Blocked hostname"):
                _validate_url(f"https://{hostname}/admin")

    def test_invalid_scheme_rejected(self) -> None:
        """Test that non-HTTP(S) schemes are rejected."""
        with pytest.raises(ToolExecutionError, match="Only HTTP"):
            _validate_url("ftp://example.com/file")

        with pytest.raises(ToolExecutionError, match="Only HTTP"):
            _validate_url("file:///etc/passwd")

        with pytest.raises(ToolExecutionError, match="Only HTTP"):
            _validate_url("gopher://example.com/")

    def test_missing_hostname_rejected(self) -> None:
        """Test that URLs without hostname are rejected."""
        with pytest.raises(ToolExecutionError, match="hostname"):
            _validate_url("https:///path/only")


class TestRedirectValidation:
    """Tests for redirect URL validation."""

    @patch("requests.get")
    @patch("socket.getaddrinfo")
    def test_redirect_to_blocked_hostname_jina(
        self,
        mock_getaddrinfo: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Test that redirects to blocked hostnames are blocked in Jina path."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("104.18.0.1", 0)),
        ]

        # Mock redirect response to localhost (blocked hostname)
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://localhost/admin"}

        mock_get.return_value = redirect_response

        # localhost is blocked by hostname check before DNS
        with pytest.raises(ToolExecutionError, match="localhost"):
            read_url.invoke({"url": "https://example.com/redirect"})

    @patch("requests.get")
    @patch("socket.getaddrinfo")
    def test_redirect_to_private_ip_blocked_jina(
        self,
        mock_getaddrinfo: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Test that redirects to private IPs are blocked in Jina path."""
        # First call for original URL - public IP
        # Second call for redirect destination - resolves to private IP
        mock_getaddrinfo.side_effect = [
            [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("104.18.0.1", 0))
            ],  # example.com
            [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))
            ],  # internal.company.com
        ]

        # Mock redirect response to internal hostname
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://internal.company.com/admin"}

        mock_get.return_value = redirect_response

        # Disable fallback to ensure Jina error propagates
        config = ReadUrlToolConfig(enable_fallback=False)
        set_read_url_config(config)

        try:
            with pytest.raises(ToolExecutionError, match=r"192\.168\.1\.1"):
                read_url.invoke({"url": "https://example.com/redirect"})
        finally:
            # Reset to default
            set_read_url_config(ReadUrlToolConfig())

    @patch("requests.get")
    @patch("socket.getaddrinfo")
    def test_redirect_to_metadata_blocked(
        self,
        mock_getaddrinfo: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Test that redirects to cloud metadata endpoints are blocked."""
        mock_getaddrinfo.side_effect = [
            [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("104.18.0.1", 0))
            ],  # r.jina.ai
            [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.169.254", 0))
            ],  # AWS metadata
        ]

        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {
            "Location": "http://169.254.169.254/latest/meta-data"
        }

        mock_get.return_value = redirect_response

        with pytest.raises(ToolExecutionError, match=r"169\.254\.169\.254"):
            read_url.invoke({"url": "https://example.com/ssrf"})

    @patch("requests.get")
    @patch("socket.getaddrinfo")
    def test_too_many_redirects(
        self,
        mock_getaddrinfo: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Test that too many redirects are rejected."""
        # All DNS lookups succeed
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("104.18.0.1", 0)),
        ]

        # Keep redirecting forever
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "https://example.com/redirect"}

        mock_get.return_value = redirect_response

        with pytest.raises(ToolExecutionError, match="Too many redirects"):
            read_url.invoke({"url": "https://example.com/loop"})


class TestReadUrlIntegration:
    """Integration tests for read_url tool."""

    @patch("requests.get")
    @patch("socket.getaddrinfo")
    def test_successful_fetch_public_url(
        self,
        mock_getaddrinfo: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Test successful fetch of public URL."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("104.18.0.1", 0)),
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Example Page\n\nThis is example content."
        mock_get.return_value = mock_response

        result = read_url.invoke({"url": "https://example.com/page"})

        assert "Example" in result

    def test_localhost_blocked_by_default(self) -> None:
        """Test that localhost is blocked without config."""
        with pytest.raises(ToolExecutionError, match="Blocked hostname"):
            read_url.invoke({"url": "http://localhost:8000/api"})

    def test_private_ip_blocked_by_default(self) -> None:
        """Test that private IPs are blocked without config."""
        with pytest.raises(ToolExecutionError, match="Loopback"):
            read_url.invoke({"url": "http://127.0.0.1:8080/admin"})

        with pytest.raises(ToolExecutionError, match="Private"):
            read_url.invoke({"url": "http://192.168.1.1/router"})

    @patch("requests.get")
    @patch("socket.getaddrinfo")
    def test_trafilatura_fallback_with_redirect_validation(
        self,
        mock_getaddrinfo: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Test trafilatura fallback path also validates redirects."""
        # All DNS lookups return public IPs
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
        ]

        # First request returns redirect to private IP
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://192.168.1.1/internal"}

        mock_get.return_value = redirect_response

        # Second DNS lookup for redirect target
        mock_getaddrinfo.side_effect = [
            [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
            ],  # original
            [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0))
            ],  # redirect
        ]

        with pytest.raises(ToolExecutionError, match=r"192\.168\.1\.1"):
            read_url.invoke(
                {"url": "https://example.com/redirect", "use_fallback": True}
            )
