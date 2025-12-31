"""Tests for standardized error code catalog (SOUL-338).

Tests the error code enum, registry, and factory functions to ensure
consistent error responses across all API endpoints.
"""

from __future__ import annotations

import re

import pytest

from consoul.server.errors import (
    ERROR_REGISTRY,
    ErrorCode,
    create_error_response,
    get_error_http_status,
)
from consoul.server.models import ChatErrorResponse, SSEErrorEvent


class TestErrorCodeRegistry:
    """Test error code definitions and registry completeness."""

    def test_all_codes_have_metadata(self) -> None:
        """Every ErrorCode enum member has a corresponding registry entry."""
        for code in ErrorCode:
            assert code in ERROR_REGISTRY, f"Missing registry entry for {code.name}"

    def test_codes_follow_format(self) -> None:
        """All error codes match the E[0-9]{3} pattern."""
        pattern = re.compile(r"^E\d{3}$")
        for code in ErrorCode:
            assert pattern.match(code.value), f"Invalid code format: {code.value}"

    def test_http_status_mappings_are_valid(self) -> None:
        """All HTTP status codes are valid 4xx or 5xx values."""
        valid_statuses = set(range(400, 600))
        for code, metadata in ERROR_REGISTRY.items():
            http_status = metadata["http_status"]
            assert http_status in valid_statuses, (
                f"Invalid HTTP status {http_status} for {code.name}"
            )

    def test_registry_has_required_fields(self) -> None:
        """Each registry entry has all required fields."""
        required_fields = {"error", "http_status", "recoverable", "message"}
        for code, metadata in ERROR_REGISTRY.items():
            assert required_fields <= set(metadata.keys()), (
                f"Missing fields in {code.name}: {required_fields - set(metadata.keys())}"
            )

    def test_error_field_is_snake_case(self) -> None:
        """Error type identifiers are snake_case strings."""
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for code, metadata in ERROR_REGISTRY.items():
            error = metadata["error"]
            assert pattern.match(error), (
                f"Invalid error format for {code.name}: {error}"
            )

    def test_recoverable_is_boolean(self) -> None:
        """Recoverable field is a boolean."""
        for code, metadata in ERROR_REGISTRY.items():
            assert isinstance(metadata["recoverable"], bool), (
                f"recoverable should be bool for {code.name}"
            )

    def test_message_is_non_empty_string(self) -> None:
        """Message field is a non-empty string."""
        for code, metadata in ERROR_REGISTRY.items():
            message = metadata["message"]
            assert isinstance(message, str), f"message should be str for {code.name}"
            assert len(message) > 0, f"message should be non-empty for {code.name}"


class TestErrorCodeCategories:
    """Test error code categorization by range."""

    def test_e0xx_are_client_errors(self) -> None:
        """E0xx codes (except E01x, E02x) map to 4xx status codes."""
        for code in ErrorCode:
            if code.value.startswith("E00") or code.value.startswith("E00"):
                status = ERROR_REGISTRY[code]["http_status"]
                # E00x should be 400-422 range
                assert 400 <= status < 500, (
                    f"{code.name} ({code.value}) should have 4xx status, got {status}"
                )

    def test_e01x_are_auth_errors(self) -> None:
        """E01x codes map to 401 Unauthorized."""
        auth_codes = [
            ErrorCode.AUTH_REQUIRED,
            ErrorCode.INVALID_API_KEY,
            ErrorCode.API_KEY_EXPIRED,
        ]
        for code in auth_codes:
            assert ERROR_REGISTRY[code]["http_status"] == 401, (
                f"{code.name} should map to 401"
            )

    def test_e02x_are_rate_limit_errors(self) -> None:
        """E02x codes map to 429 Too Many Requests."""
        rate_limit_codes = [
            ErrorCode.RATE_LIMIT_EXCEEDED,
            ErrorCode.RATE_LIMIT_TIER_EXHAUSTED,
        ]
        for code in rate_limit_codes:
            assert ERROR_REGISTRY[code]["http_status"] == 429, (
                f"{code.name} should map to 429"
            )
            assert ERROR_REGISTRY[code]["recoverable"] is True, (
                f"{code.name} should be recoverable"
            )

    def test_e9xx_are_internal_errors(self) -> None:
        """E9xx codes map to 5xx status codes."""
        internal_codes = [
            ErrorCode.INTERNAL_ERROR,
            ErrorCode.UNEXPECTED_EXCEPTION,
            ErrorCode.UNKNOWN_ERROR,
        ]
        for code in internal_codes:
            status = ERROR_REGISTRY[code]["http_status"]
            assert 500 <= status < 600, (
                f"{code.name} should have 5xx status, got {status}"
            )


class TestGetErrorHttpStatus:
    """Test get_error_http_status function."""

    def test_returns_correct_status(self) -> None:
        """Returns HTTP status from registry."""
        assert get_error_http_status(ErrorCode.INVALID_API_KEY) == 401
        assert get_error_http_status(ErrorCode.RATE_LIMIT_EXCEEDED) == 429
        assert get_error_http_status(ErrorCode.INTERNAL_ERROR) == 500
        assert get_error_http_status(ErrorCode.SESSION_STORAGE_UNAVAILABLE) == 503


class TestCreateErrorResponse:
    """Test create_error_response factory function."""

    def test_creates_valid_response_with_defaults(self) -> None:
        """Response has all required fields with default values."""
        response = create_error_response(ErrorCode.INTERNAL_ERROR)

        assert response["code"] == "E900"
        assert response["error"] == "internal_error"
        assert response["message"] == "Internal server error"
        assert response["recoverable"] is False
        assert response["retry_after"] is None
        assert response["details"] is None
        assert "timestamp" in response

    def test_custom_message_override(self) -> None:
        """Custom message replaces default."""
        response = create_error_response(
            ErrorCode.INTERNAL_ERROR,
            message="Something went wrong",
        )
        assert response["message"] == "Something went wrong"
        # Other fields remain default
        assert response["code"] == "E900"
        assert response["error"] == "internal_error"

    def test_retry_after_for_recoverable_errors(self) -> None:
        """Recoverable errors can include retry_after."""
        response = create_error_response(
            ErrorCode.SESSION_STORAGE_UNAVAILABLE,
            retry_after=30,
        )
        assert response["retry_after"] == 30
        assert response["recoverable"] is True

    def test_details_field(self) -> None:
        """Details field includes additional context."""
        response = create_error_response(
            ErrorCode.REQUEST_TOO_LARGE,
            details={"limit": 1048576, "received": 2000000},
        )
        assert response["details"] == {"limit": 1048576, "received": 2000000}

    def test_timestamp_is_iso_format(self) -> None:
        """Timestamp is ISO 8601 format."""
        response = create_error_response(ErrorCode.INTERNAL_ERROR)
        # Should be parseable as ISO 8601
        assert "T" in response["timestamp"]
        assert response["timestamp"].endswith("Z") or "+" in response["timestamp"]

    def test_all_error_codes_produce_valid_response(self) -> None:
        """All error codes can be used to create responses."""
        for code in ErrorCode:
            response = create_error_response(code)
            assert response["code"] == code.value
            assert "error" in response
            assert "message" in response
            assert "recoverable" in response
            assert "timestamp" in response


class TestChatErrorResponseModel:
    """Test updated ChatErrorResponse Pydantic model."""

    def test_model_has_new_fields(self) -> None:
        """ChatErrorResponse includes code, recoverable, retry_after, details."""
        fields = ChatErrorResponse.model_fields
        assert "code" in fields
        assert "error" in fields
        assert "message" in fields
        assert "recoverable" in fields
        assert "retry_after" in fields
        assert "details" in fields
        assert "timestamp" in fields

    def test_model_validates_successfully(self) -> None:
        """Model can be instantiated with valid data."""
        error = ChatErrorResponse(
            code="E110",
            error="session_storage_unavailable",
            message="Session storage temporarily unavailable",
            recoverable=True,
            retry_after=30,
            timestamp="2025-12-31T00:00:00Z",
        )
        assert error.code == "E110"
        assert error.recoverable is True
        assert error.retry_after == 30

    def test_model_optional_fields(self) -> None:
        """Optional fields default to None."""
        error = ChatErrorResponse(
            code="E900",
            error="internal_error",
            message="Internal error",
            recoverable=False,
            timestamp="2025-12-31T00:00:00Z",
        )
        assert error.retry_after is None
        assert error.details is None


class TestSSEErrorEventModel:
    """Test updated SSEErrorEvent Pydantic model."""

    def test_model_has_new_fields(self) -> None:
        """SSEErrorEvent includes code, error, message, recoverable."""
        fields = SSEErrorEvent.model_fields
        assert "code" in fields
        assert "error" in fields
        assert "message" in fields
        assert "recoverable" in fields

    def test_model_validates_successfully(self) -> None:
        """Model can be instantiated with valid data."""
        event = SSEErrorEvent(
            code="E900",
            error="internal_error",
            message="An error occurred",
            recoverable=False,
        )
        assert event.code == "E900"
        assert event.error == "internal_error"
        assert event.recoverable is False

    def test_recoverable_defaults_to_false(self) -> None:
        """Recoverable field defaults to False."""
        event = SSEErrorEvent(
            code="E900",
            error="internal_error",
            message="An error occurred",
        )
        assert event.recoverable is False


class TestSpecificErrorCodes:
    """Test specific error codes mentioned in the ticket."""

    @pytest.mark.parametrize(
        ("code", "expected_error", "expected_status"),
        [
            (ErrorCode.INVALID_REQUEST_BODY, "invalid_request_body", 422),
            (ErrorCode.MISSING_REQUIRED_FIELD, "missing_required_field", 422),
            (ErrorCode.FIELD_VALIDATION_FAILED, "field_validation_failed", 422),
            (ErrorCode.SESSION_ID_INVALID, "session_id_invalid", 400),
            (ErrorCode.MESSAGE_TOO_LONG, "message_too_long", 400),
            (ErrorCode.AUTH_REQUIRED, "auth_required", 401),
            (ErrorCode.INVALID_API_KEY, "invalid_api_key", 401),
            (ErrorCode.RATE_LIMIT_EXCEEDED, "rate_limit_exceeded", 429),
            (ErrorCode.SESSION_NOT_FOUND, "session_not_found", 404),
            (ErrorCode.SESSION_EXPIRED, "session_expired", 410),
            (ErrorCode.SESSION_LOCKED, "session_locked", 409),
            (ErrorCode.SESSION_STORAGE_UNAVAILABLE, "session_storage_unavailable", 503),
            (ErrorCode.LLM_UNAVAILABLE, "llm_unavailable", 503),
            (ErrorCode.LLM_TIMEOUT, "llm_timeout", 504),
            (ErrorCode.TOOL_NOT_FOUND, "tool_not_found", 400),
            (ErrorCode.TOOL_DENIED, "tool_denied", 403),
            (ErrorCode.INTERNAL_ERROR, "internal_error", 500),
        ],
    )
    def test_error_code_mappings(
        self, code: ErrorCode, expected_error: str, expected_status: int
    ) -> None:
        """Verify specific error codes have correct mappings."""
        metadata = ERROR_REGISTRY[code]
        assert metadata["error"] == expected_error
        assert metadata["http_status"] == expected_status


class TestRecoverableErrors:
    """Test recoverability classification."""

    def test_session_storage_is_recoverable(self) -> None:
        """Session storage errors are recoverable."""
        assert (
            ERROR_REGISTRY[ErrorCode.SESSION_STORAGE_UNAVAILABLE]["recoverable"] is True
        )
        assert ERROR_REGISTRY[ErrorCode.SESSION_SAVE_FAILED]["recoverable"] is True
        assert ERROR_REGISTRY[ErrorCode.SESSION_LOCKED]["recoverable"] is True

    def test_llm_transient_errors_are_recoverable(self) -> None:
        """LLM transient errors are recoverable."""
        assert ERROR_REGISTRY[ErrorCode.LLM_UNAVAILABLE]["recoverable"] is True
        assert ERROR_REGISTRY[ErrorCode.LLM_TIMEOUT]["recoverable"] is True
        assert ERROR_REGISTRY[ErrorCode.LLM_RATE_LIMITED]["recoverable"] is True

    def test_rate_limit_errors_are_recoverable(self) -> None:
        """Rate limit errors are recoverable."""
        assert ERROR_REGISTRY[ErrorCode.RATE_LIMIT_EXCEEDED]["recoverable"] is True
        assert (
            ERROR_REGISTRY[ErrorCode.RATE_LIMIT_TIER_EXHAUSTED]["recoverable"] is True
        )

    def test_validation_errors_are_not_recoverable(self) -> None:
        """Validation errors are not recoverable."""
        assert ERROR_REGISTRY[ErrorCode.INVALID_REQUEST_BODY]["recoverable"] is False
        assert ERROR_REGISTRY[ErrorCode.FIELD_VALIDATION_FAILED]["recoverable"] is False
        assert ERROR_REGISTRY[ErrorCode.MESSAGE_TOO_LONG]["recoverable"] is False

    def test_auth_errors_are_not_recoverable(self) -> None:
        """Auth errors are not recoverable without fixing the request."""
        assert ERROR_REGISTRY[ErrorCode.AUTH_REQUIRED]["recoverable"] is False
        assert ERROR_REGISTRY[ErrorCode.INVALID_API_KEY]["recoverable"] is False
