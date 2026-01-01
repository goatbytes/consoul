"""Tests for webhook URL validation and SSRF protection."""

from __future__ import annotations

import pytest

from consoul.server.webhooks.security import (
    URLValidationError,
    WebhookURLValidator,
    is_safe_url,
)


class TestWebhookURLValidator:
    """Tests for WebhookURLValidator class."""

    def test_valid_https_url(self) -> None:
        """Test validation of valid HTTPS URL."""
        validator = WebhookURLValidator()

        result = validator.validate("https://example.com/webhook")

        assert result.url == "https://example.com/webhook"
        assert result.host == "example.com"
        assert len(result.resolved_ips) > 0

    def test_http_url_rejected_by_default(self) -> None:
        """Test that HTTP URLs are rejected by default."""
        validator = WebhookURLValidator()

        with pytest.raises(URLValidationError, match="HTTPS"):
            validator.validate("http://example.com/webhook")

    def test_http_allowed_when_configured(self) -> None:
        """Test that HTTP URLs can be allowed."""
        validator = WebhookURLValidator(allow_http=True)

        result = validator.validate("http://example.com/webhook")

        assert result.host == "example.com"

    def test_localhost_rejected_by_default(self) -> None:
        """Test that localhost is rejected by default."""
        validator = WebhookURLValidator()

        with pytest.raises(URLValidationError, match="not allowed"):
            validator.validate("https://localhost/webhook")

    def test_localhost_allowed_when_configured(self) -> None:
        """Test that localhost can be allowed for development."""
        validator = WebhookURLValidator(allow_localhost=True, allow_http=True)

        result = validator.validate("http://localhost:8000/webhook")

        assert result.host == "localhost"

    def test_private_ip_rejected(self) -> None:
        """Test that private IPs are rejected."""
        validator = WebhookURLValidator()

        # 10.x.x.x range
        with pytest.raises(URLValidationError, match="Private IP"):
            validator.validate("https://10.0.0.1/webhook")

        # 172.16.x.x range
        with pytest.raises(URLValidationError, match="Private IP"):
            validator.validate("https://172.16.0.1/webhook")

        # 192.168.x.x range
        with pytest.raises(URLValidationError, match="Private IP"):
            validator.validate("https://192.168.1.1/webhook")

    def test_metadata_ip_rejected(self) -> None:
        """Test that cloud metadata IPs are rejected."""
        validator = WebhookURLValidator()

        with pytest.raises(URLValidationError, match="metadata"):
            validator.validate("https://169.254.169.254/latest/meta-data")

    def test_invalid_url_format(self) -> None:
        """Test rejection of invalid URL formats."""
        validator = WebhookURLValidator()

        with pytest.raises(URLValidationError):
            validator.validate("not-a-url")

    def test_missing_hostname(self) -> None:
        """Test rejection of URL without hostname."""
        validator = WebhookURLValidator()

        with pytest.raises(URLValidationError, match="hostname"):
            validator.validate("https:///path/only")

    def test_invalid_scheme(self) -> None:
        """Test rejection of invalid schemes."""
        validator = WebhookURLValidator(allow_http=True)

        with pytest.raises(URLValidationError, match="scheme"):
            validator.validate("ftp://example.com/webhook")


class TestValidateRedirect:
    """Tests for redirect validation."""

    def test_same_host_redirect_allowed(self) -> None:
        """Test that same-host redirects are allowed."""
        validator = WebhookURLValidator()

        result = validator.validate_redirect(
            original_url="https://example.com/webhook",
            redirect_url="https://example.com/new-path",
            redirect_count=1,
        )

        assert result.host == "example.com"

    def test_cross_host_redirect_rejected(self) -> None:
        """Test that cross-host redirects are rejected."""
        validator = WebhookURLValidator()

        with pytest.raises(URLValidationError, match="Cross-host"):
            validator.validate_redirect(
                original_url="https://example.com/webhook",
                redirect_url="https://evil.com/hook",
                redirect_count=1,
            )

    def test_max_redirects_enforced(self) -> None:
        """Test that max redirect limit is enforced."""
        validator = WebhookURLValidator(max_redirects=3)

        with pytest.raises(URLValidationError, match="Too many redirects"):
            validator.validate_redirect(
                original_url="https://example.com/webhook",
                redirect_url="https://example.com/path",
                redirect_count=3,
            )


class TestIsSafeUrl:
    """Tests for is_safe_url helper function."""

    def test_safe_url(self) -> None:
        """Test that safe URLs return True."""
        assert is_safe_url("https://example.com/webhook") is True

    def test_unsafe_url(self) -> None:
        """Test that unsafe URLs return False."""
        # Private IP
        assert is_safe_url("https://192.168.1.1/webhook") is False

        # HTTP
        assert is_safe_url("http://example.com/webhook") is False

        # Localhost
        assert is_safe_url("https://localhost/webhook") is False

    def test_localhost_with_flag(self) -> None:
        """Test localhost allowance flag."""
        # is_safe_url requires HTTPS by default, use HTTPS localhost check
        validator = WebhookURLValidator(allow_localhost=True, allow_http=True)
        result = validator.validate("http://localhost:8000/webhook")
        assert result.host == "localhost"
