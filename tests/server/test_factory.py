"""Tests for server factory pattern.

Tests the create_server() factory function and all its components:
- Configuration loading (default and custom)
- Middleware integration (CORS, auth, rate limiting)
- Health and readiness endpoints
- App state storage (limiter, auth)
- Graceful shutdown handling
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from consoul.server import create_server
from consoul.server.models import (
    CORSConfig,
    RateLimitConfig,
    SecurityConfig,
    ServerConfig,
)


class TestServerFactory:
    """Test server factory function."""

    def test_create_server_default_config(self) -> None:
        """Factory creates server with default config."""
        app = create_server()

        assert isinstance(app, FastAPI)
        assert app.title == "Consoul API"  # Default app_name
        assert hasattr(app.state, "limiter")
        assert hasattr(app.state, "auth")

    def test_create_server_custom_config(self) -> None:
        """Factory accepts custom ServerConfig."""
        config = ServerConfig(app_name="Custom API")
        app = create_server(config)

        assert app.title == "Custom API"
        assert hasattr(app.state, "limiter")

    def test_create_server_version_metadata(self) -> None:
        """Server version extracted from package metadata."""
        app = create_server()
        assert app.version  # Should have a version
        # Version should be a string like "0.4.2" or "unknown"
        assert isinstance(app.version, str)

    def test_limiter_always_configured(self) -> None:
        """Rate limiter always configured and stored in app.state."""
        app = create_server()

        assert hasattr(app.state, "limiter")
        assert app.state.limiter is not None

    def test_auth_configured_with_api_keys(self) -> None:
        """Auth stored in app.state when api_keys provided."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-key"]))
        app = create_server(config)

        assert hasattr(app.state, "auth")
        assert app.state.auth is not None
        assert "test-key" in app.state.auth.api_keys

    def test_auth_none_without_api_keys(self) -> None:
        """Auth is None when no api_keys provided."""
        config = ServerConfig(security=SecurityConfig(api_keys=[]))
        app = create_server(config)

        assert hasattr(app.state, "auth")
        assert app.state.auth is None

    def test_cors_configured(self) -> None:
        """CORS middleware configured from config."""
        config = ServerConfig(cors=CORSConfig(allowed_origins=["https://example.com"]))
        app = create_server(config)

        client = TestClient(app)
        response = client.options("/health", headers={"Origin": "https://example.com"})

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_rate_limit_custom_config(self) -> None:
        """Rate limiter uses custom configuration."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["100/minute"]))
        app = create_server(config)

        assert app.state.limiter is not None
        # Default limits stored in limiter config
        assert "100" in str(app.state.limiter.default_limits)


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_endpoint_exists(self) -> None:
        """Health endpoint is registered."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_response(self) -> None:
        """Health endpoint returns correct response."""
        config = ServerConfig(app_name="Test API")
        app = create_server(config)
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        assert data["status"] == "ok"
        assert data["service"] == "Test API"
        assert "version" in data

    def test_health_bypasses_auth(self) -> None:
        """Health endpoint bypasses authentication."""
        config = ServerConfig(security=SecurityConfig(api_keys=["secret"]))
        app = create_server(config)
        client = TestClient(app)

        # Should succeed without API key
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_bypasses_rate_limiting(self) -> None:
        """Health endpoint exempt from rate limits."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["1/minute"]))
        app = create_server(config)
        client = TestClient(app)

        # Hit health endpoint many times (more than rate limit)
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200  # Never 429


class TestReadinessEndpoint:
    """Test /ready endpoint."""

    def test_ready_endpoint_exists(self) -> None:
        """Readiness endpoint is registered."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/ready")
        assert response.status_code == 200

    def test_ready_endpoint_no_dependencies(self) -> None:
        """Ready endpoint succeeds when no dependencies configured."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/ready")
        data = response.json()

        assert data["status"] == "ready"
        assert "checks" in data

    def test_ready_bypasses_auth(self) -> None:
        """Ready endpoint bypasses authentication."""
        config = ServerConfig(security=SecurityConfig(api_keys=["secret"]))
        app = create_server(config)
        client = TestClient(app)

        # Should succeed without API key
        response = client.get("/ready")
        assert response.status_code == 200

    def test_ready_bypasses_rate_limiting(self) -> None:
        """Ready endpoint exempt from rate limits."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["1/minute"]))
        app = create_server(config)
        client = TestClient(app)

        # Hit ready endpoint many times
        for _ in range(10):
            response = client.get("/ready")
            assert response.status_code == 200  # Never 429

    @pytest.mark.skip(reason="Requires Redis connection - integration test only")
    def test_ready_redis_health_check(self) -> None:
        """Ready endpoint checks Redis health when configured."""
        # This test requires a running Redis instance
        config = ServerConfig(
            rate_limit=RateLimitConfig(storage_url="redis://localhost:6379")
        )
        app = create_server(config)
        client = TestClient(app)

        response = client.get("/ready")

        # Should check Redis and return status
        data = response.json()
        assert "checks" in data
        assert "redis" in data["checks"]


class TestAuthIntegration:
    """Test authentication integration."""

    def test_auth_dependency_available(self) -> None:
        """Auth instance available for route dependencies."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-key"]))
        app = create_server(config)

        # Verify auth is available and configured
        assert app.state.auth is not None
        assert "test-key" in app.state.auth.api_keys

        # Verify auth.verify can be used as a dependency
        assert callable(app.state.auth.verify)

    def test_auth_bypass_paths_configured(self) -> None:
        """Auth bypass paths include health endpoints."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-key"]))
        app = create_server(config)

        assert app.state.auth is not None
        # Default bypass paths should include health
        assert "/health" in app.state.auth.bypass_paths


class TestRateLimitIntegration:
    """Test rate limiting integration."""

    def test_limiter_decorator_available(self) -> None:
        """Limiter available for route decorators."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["2/minute"]))
        app = create_server(config)

        # Verify limiter is available and configured
        assert app.state.limiter is not None
        assert hasattr(app.state.limiter, "limit")
        assert callable(app.state.limiter.limit)

    def test_limiter_key_func(self) -> None:
        """Rate limiter uses default key function."""
        app = create_server()

        # Limiter should have a key function
        assert app.state.limiter is not None
        assert hasattr(app.state.limiter, "key_func")


class TestLifecycleManagement:
    """Test application lifecycle (startup/shutdown)."""

    def test_lifespan_context_executes(self) -> None:
        """Lifespan context executes on startup/shutdown."""
        app = create_server()

        # TestClient triggers lifespan context
        with TestClient(app) as client:
            # Server should be running
            response = client.get("/health")
            assert response.status_code == 200

        # Lifespan shutdown executed (TestClient closes connection)

    def test_multiple_client_connections(self) -> None:
        """Multiple clients can connect to server."""
        app = create_server()

        # Create multiple clients
        with TestClient(app) as client1, TestClient(app) as client2:
            # Both clients should work
            assert client1.get("/health").status_code == 200
            assert client2.get("/health").status_code == 200


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_config_uses_defaults(self) -> None:
        """Passing None for config uses ServerConfig defaults."""
        app = create_server(None)

        assert isinstance(app, FastAPI)
        assert app.title == "Consoul API"

    def test_empty_api_keys_list(self) -> None:
        """Empty API keys list disables authentication."""
        config = ServerConfig(security=SecurityConfig(api_keys=[]))
        app = create_server(config)

        assert app.state.auth is None

    def test_custom_bypass_paths(self) -> None:
        """Custom bypass paths respected."""
        config = ServerConfig(
            security=SecurityConfig(
                api_keys=["key"], bypass_paths=["/health", "/custom"]
            )
        )
        app = create_server(config)

        assert "/custom" in app.state.auth.bypass_paths

    def test_docs_disabled_with_auth(self) -> None:
        """API docs disabled when authentication enabled."""
        config = ServerConfig(security=SecurityConfig(api_keys=["key"]))
        app = create_server(config)

        # docs_url should be None (disabled)
        assert app.docs_url is None
        assert app.redoc_url is None

    def test_docs_enabled_without_auth(self) -> None:
        """API docs disabled in factory (security best practice)."""
        config = ServerConfig(security=SecurityConfig(api_keys=[]))
        app = create_server(config)

        # docs are disabled even without auth (production best practice)
        assert app.docs_url is None


class TestHealthEndpointSchema:
    """Test /health endpoint response schema."""

    def test_health_response_schema(self) -> None:
        """Health endpoint returns all required fields."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        # Verify all required fields present
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data

    def test_health_timestamp_format(self) -> None:
        """Health endpoint returns ISO 8601 timestamp."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        # Verify ISO 8601 format (should parse without error)
        timestamp = data["timestamp"]
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed is not None

    def test_health_status_always_ok(self) -> None:
        """Health endpoint status field is always 'ok'."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        assert data["status"] == "ok"

    def test_health_service_name_from_config(self) -> None:
        """Health endpoint service name matches config."""
        config = ServerConfig(app_name="Custom Service Name")
        app = create_server(config)
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        assert data["service"] == "Custom Service Name"

    def test_health_version_populated(self) -> None:
        """Health endpoint version field is not empty."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        assert data["version"]
        assert isinstance(data["version"], str)


class TestReadinessEndpointSchema:
    """Test /ready endpoint response schemas."""

    def test_ready_response_schema_success(self) -> None:
        """Readiness endpoint returns correct schema on success."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/ready")
        data = response.json()

        # Verify success schema fields
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data
        assert data["status"] == "ready"

    def test_ready_timestamp_format(self) -> None:
        """Readiness endpoint returns ISO 8601 timestamp."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/ready")
        data = response.json()

        # Verify ISO 8601 format
        timestamp = data["timestamp"]
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed is not None

    def test_ready_checks_field_present(self) -> None:
        """Readiness endpoint includes checks dictionary."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/ready")
        data = response.json()

        assert "checks" in data
        assert isinstance(data["checks"], dict)

    def test_ready_no_dependencies_response(self) -> None:
        """Readiness endpoint returns valid response with no dependencies."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/ready")
        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "ready"
        assert "checks" in data

    @pytest.mark.skip(reason="Requires Redis connection - integration test only")
    def test_ready_response_schema_error(self) -> None:
        """Readiness endpoint returns correct schema on error."""
        # Mock Redis failure
        with patch(
            "consoul.server.factory.check_redis_connection",
            new=AsyncMock(return_value=False),
        ):
            config = ServerConfig(
                rate_limit=RateLimitConfig(storage_url="redis://localhost:6379")
            )
            app = create_server(config)
            client = TestClient(app)

            response = client.get("/ready")
            data = response.json()

            # Verify error schema fields
            assert response.status_code == 503
            assert "status" in data
            assert "checks" in data
            assert "message" in data
            assert "timestamp" in data
            assert data["status"] == "not_ready"


class TestAuthBypassVerification:
    """Test authentication bypass for health/readiness endpoints."""

    def test_health_in_bypass_paths(self) -> None:
        """Health endpoint path is in auth bypass list."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-key"]))
        app = create_server(config)

        assert app.state.auth is not None
        assert "/health" in app.state.auth.bypass_paths

    def test_ready_in_bypass_paths(self) -> None:
        """Readiness endpoint path is in auth bypass list."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-key"]))
        app = create_server(config)

        assert app.state.auth is not None
        assert "/ready" in app.state.auth.bypass_paths

    def test_health_accessible_without_api_key(self) -> None:
        """Health endpoint returns 200 without API key."""
        config = ServerConfig(security=SecurityConfig(api_keys=["secret-key"]))
        app = create_server(config)
        client = TestClient(app)

        # No API key header
        response = client.get("/health")
        assert response.status_code == 200

    def test_ready_accessible_without_api_key(self) -> None:
        """Readiness endpoint returns 200 without API key."""
        config = ServerConfig(security=SecurityConfig(api_keys=["secret-key"]))
        app = create_server(config)
        client = TestClient(app)

        # No API key header
        response = client.get("/ready")
        assert response.status_code == 200

    def test_health_bypasses_invalid_api_key(self) -> None:
        """Health endpoint works even with invalid API key."""
        config = ServerConfig(security=SecurityConfig(api_keys=["valid-key"]))
        app = create_server(config)
        client = TestClient(app)

        # Invalid API key
        response = client.get("/health", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 200

    def test_ready_bypasses_invalid_api_key(self) -> None:
        """Readiness endpoint works even with invalid API key."""
        config = ServerConfig(security=SecurityConfig(api_keys=["valid-key"]))
        app = create_server(config)
        client = TestClient(app)

        # Invalid API key
        response = client.get("/ready", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 200


class TestRateLimitExemptionVerification:
    """Test rate limit exemption for health/readiness endpoints."""

    def test_health_never_rate_limited(self) -> None:
        """Health endpoint never returns 429 even under load."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["1/minute"]))
        app = create_server(config)
        client = TestClient(app)

        # Hit endpoint 100 times (far exceeds rate limit)
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200  # Never 429

    def test_ready_never_rate_limited(self) -> None:
        """Readiness endpoint never returns 429 even under load."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["1/minute"]))
        app = create_server(config)
        client = TestClient(app)

        # Hit endpoint 100 times (far exceeds rate limit)
        for _ in range(100):
            response = client.get("/ready")
            assert response.status_code == 200  # Never 429

    def test_health_exempt_with_strict_limits(self) -> None:
        """Health endpoint works with very strict rate limits."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["1/hour"]))
        app = create_server(config)
        client = TestClient(app)

        # Multiple requests should all succeed
        for _ in range(50):
            response = client.get("/health")
            assert response.status_code == 200

    def test_ready_exempt_with_strict_limits(self) -> None:
        """Readiness endpoint works with very strict rate limits."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["1/hour"]))
        app = create_server(config)
        client = TestClient(app)

        # Multiple requests should all succeed
        for _ in range(50):
            response = client.get("/ready")
            assert response.status_code == 200


class TestIntegration:
    """Integration tests for full server functionality."""

    def test_full_server_startup(self) -> None:
        """Complete server startup with all components."""
        config = ServerConfig(
            app_name="Integration Test API",
            security=SecurityConfig(api_keys=["integration-key"]),
            rate_limit=RateLimitConfig(default_limits=["100/minute"]),
            cors=CORSConfig(allowed_origins=["https://example.com"]),
        )
        app = create_server(config)

        # Verify all components initialized
        assert app.title == "Integration Test API"
        assert app.state.limiter is not None
        assert app.state.auth is not None

        # Test with client
        with TestClient(app) as client:
            # Health check works
            assert client.get("/health").status_code == 200

            # Readiness check works
            assert client.get("/ready").status_code == 200

    def test_authenticated_workflow(self) -> None:
        """Complete workflow with authentication."""
        config = ServerConfig(security=SecurityConfig(api_keys=["workflow-key"]))
        app = create_server(config)

        client = TestClient(app)

        # Health check works without auth
        assert client.get("/health").status_code == 200

        # Readiness check works without auth
        assert client.get("/ready").status_code == 200

        # Verify auth is configured
        assert app.state.auth is not None
        assert "workflow-key" in app.state.auth.api_keys

    def test_rate_limited_workflow(self) -> None:
        """Complete workflow with rate limiting."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["3/minute"]))
        app = create_server(config)

        client = TestClient(app)

        # Verify rate limiter is configured
        assert app.state.limiter is not None

        # Health endpoint works (exempt from rate limiting)
        assert client.get("/health").status_code == 200

        # Readiness endpoint works (exempt from rate limiting)
        assert client.get("/ready").status_code == 200
