"""Standardized error code catalog for the Consoul Server API.

Provides unique error codes (E001-E999) with consistent categorization,
HTTP status mapping, and recovery guidance for all API endpoints.

Error Code Ranges:
    E0xx: Client validation errors (4xx)
    E01x: Authentication errors (401)
    E02x: Rate limiting errors (429)
    E1xx: Session errors (4xx/5xx)
    E2xx: LLM provider errors (5xx)
    E3xx: Tool execution errors
    E9xx: Internal errors (5xx)

Example:
    >>> from consoul.server.errors import ErrorCode, create_error_response
    >>> response = create_error_response(
    ...     ErrorCode.SESSION_STORAGE_UNAVAILABLE,
    ...     retry_after=30,
    ... )
    >>> print(response["code"])
    'E110'
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

__all__ = [
    "ERROR_REGISTRY",
    "ErrorCode",
    "create_error_response",
    "get_error_http_status",
]


class ErrorCode(str, Enum):
    """Standardized error codes (E001-E999).

    Each code maps to a specific error category with consistent
    HTTP status, recoverability, and default messaging.
    """

    # E0xx - Client Validation Errors (4xx)
    INVALID_REQUEST_BODY = "E001"
    MISSING_REQUIRED_FIELD = "E002"
    FIELD_VALIDATION_FAILED = "E003"
    SESSION_ID_INVALID = "E004"
    MESSAGE_TOO_LONG = "E005"
    REQUEST_TOO_LARGE = "E006"

    # E01x - Authentication Errors (401)
    AUTH_REQUIRED = "E010"
    INVALID_API_KEY = "E011"
    API_KEY_EXPIRED = "E012"

    # E02x - Rate Limiting Errors (429)
    RATE_LIMIT_EXCEEDED = "E020"
    RATE_LIMIT_TIER_EXHAUSTED = "E021"

    # E1xx - Session Errors (4xx/5xx)
    SESSION_NOT_FOUND = "E100"
    SESSION_EXPIRED = "E101"
    SESSION_LOCKED = "E102"
    SESSION_STORAGE_UNAVAILABLE = "E110"
    SESSION_SAVE_FAILED = "E111"

    # E2xx - LLM Provider Errors (5xx)
    LLM_UNAVAILABLE = "E200"
    LLM_TIMEOUT = "E201"
    LLM_RATE_LIMITED = "E202"
    LLM_CONTEXT_TOO_LONG = "E203"
    LLM_CONTENT_FILTERED = "E204"
    CIRCUIT_BREAKER_OPEN = "E206"
    CIRCUIT_BREAKER_HALF_OPEN = "E207"
    MODEL_NOT_AVAILABLE = "E210"
    MODEL_CONFIG_ERROR = "E211"

    # E3xx - Tool Execution Errors
    TOOL_NOT_FOUND = "E300"
    TOOL_DENIED = "E301"
    TOOL_TIMEOUT = "E302"
    TOOL_EXECUTION_FAILED = "E303"

    # E9xx - Internal Errors (5xx)
    INTERNAL_ERROR = "E900"
    UNEXPECTED_EXCEPTION = "E901"
    UNKNOWN_ERROR = "E999"


# Error metadata registry with default values for each error code
ERROR_REGISTRY: dict[ErrorCode, dict[str, Any]] = {
    # E0xx - Client Validation Errors
    ErrorCode.INVALID_REQUEST_BODY: {
        "error": "invalid_request_body",
        "http_status": 422,
        "recoverable": False,
        "message": "Invalid request body format",
    },
    ErrorCode.MISSING_REQUIRED_FIELD: {
        "error": "missing_required_field",
        "http_status": 422,
        "recoverable": False,
        "message": "Required field is missing",
    },
    ErrorCode.FIELD_VALIDATION_FAILED: {
        "error": "field_validation_failed",
        "http_status": 422,
        "recoverable": False,
        "message": "Field validation failed",
    },
    ErrorCode.SESSION_ID_INVALID: {
        "error": "session_id_invalid",
        "http_status": 400,
        "recoverable": False,
        "message": "Invalid session ID format",
    },
    ErrorCode.MESSAGE_TOO_LONG: {
        "error": "message_too_long",
        "http_status": 400,
        "recoverable": False,
        "message": "Message exceeds maximum length",
    },
    ErrorCode.REQUEST_TOO_LARGE: {
        "error": "request_too_large",
        "http_status": 413,
        "recoverable": False,
        "message": "Request body exceeds size limit",
    },
    # E01x - Authentication Errors
    ErrorCode.AUTH_REQUIRED: {
        "error": "auth_required",
        "http_status": 401,
        "recoverable": False,
        "message": "Authentication required",
    },
    ErrorCode.INVALID_API_KEY: {
        "error": "invalid_api_key",
        "http_status": 401,
        "recoverable": False,
        "message": "Invalid or missing API key",
    },
    ErrorCode.API_KEY_EXPIRED: {
        "error": "api_key_expired",
        "http_status": 401,
        "recoverable": False,
        "message": "API key has expired",
    },
    # E02x - Rate Limiting Errors
    ErrorCode.RATE_LIMIT_EXCEEDED: {
        "error": "rate_limit_exceeded",
        "http_status": 429,
        "recoverable": True,
        "message": "Rate limit exceeded",
    },
    ErrorCode.RATE_LIMIT_TIER_EXHAUSTED: {
        "error": "rate_limit_tier_exhausted",
        "http_status": 429,
        "recoverable": True,
        "message": "Rate limit tier exhausted",
    },
    # E1xx - Session Errors
    ErrorCode.SESSION_NOT_FOUND: {
        "error": "session_not_found",
        "http_status": 404,
        "recoverable": False,
        "message": "Session not found",
    },
    ErrorCode.SESSION_EXPIRED: {
        "error": "session_expired",
        "http_status": 410,
        "recoverable": False,
        "message": "Session has expired",
    },
    ErrorCode.SESSION_LOCKED: {
        "error": "session_locked",
        "http_status": 409,
        "recoverable": True,
        "message": "Session is currently locked by another request",
    },
    ErrorCode.SESSION_STORAGE_UNAVAILABLE: {
        "error": "session_storage_unavailable",
        "http_status": 503,
        "recoverable": True,
        "message": "Session storage temporarily unavailable",
    },
    ErrorCode.SESSION_SAVE_FAILED: {
        "error": "session_save_failed",
        "http_status": 503,
        "recoverable": True,
        "message": "Failed to save session state",
    },
    # E2xx - LLM Provider Errors
    ErrorCode.LLM_UNAVAILABLE: {
        "error": "llm_unavailable",
        "http_status": 503,
        "recoverable": True,
        "message": "LLM provider is unavailable",
    },
    ErrorCode.LLM_TIMEOUT: {
        "error": "llm_timeout",
        "http_status": 504,
        "recoverable": True,
        "message": "LLM request timed out",
    },
    ErrorCode.LLM_RATE_LIMITED: {
        "error": "llm_rate_limited",
        "http_status": 503,
        "recoverable": True,
        "message": "LLM provider rate limit reached",
    },
    ErrorCode.LLM_CONTEXT_TOO_LONG: {
        "error": "llm_context_too_long",
        "http_status": 400,
        "recoverable": False,
        "message": "Context exceeds model's maximum length",
    },
    ErrorCode.LLM_CONTENT_FILTERED: {
        "error": "llm_content_filtered",
        "http_status": 400,
        "recoverable": False,
        "message": "Content was filtered by the LLM provider",
    },
    ErrorCode.CIRCUIT_BREAKER_OPEN: {
        "error": "circuit_breaker_open",
        "http_status": 503,
        "recoverable": True,
        "message": "LLM provider temporarily unavailable (circuit breaker open)",
    },
    ErrorCode.CIRCUIT_BREAKER_HALF_OPEN: {
        "error": "circuit_breaker_half_open",
        "http_status": 503,
        "recoverable": True,
        "message": "LLM provider testing recovery (limited capacity)",
    },
    ErrorCode.MODEL_NOT_AVAILABLE: {
        "error": "model_not_available",
        "http_status": 503,
        "recoverable": True,
        "message": "Requested model is not available",
    },
    ErrorCode.MODEL_CONFIG_ERROR: {
        "error": "model_config_error",
        "http_status": 500,
        "recoverable": False,
        "message": "Model configuration error",
    },
    # E3xx - Tool Execution Errors
    ErrorCode.TOOL_NOT_FOUND: {
        "error": "tool_not_found",
        "http_status": 400,
        "recoverable": False,
        "message": "Requested tool not found",
    },
    ErrorCode.TOOL_DENIED: {
        "error": "tool_denied",
        "http_status": 403,
        "recoverable": False,
        "message": "Tool execution was denied",
    },
    ErrorCode.TOOL_TIMEOUT: {
        "error": "tool_timeout",
        "http_status": 504,
        "recoverable": True,
        "message": "Tool execution timed out",
    },
    ErrorCode.TOOL_EXECUTION_FAILED: {
        "error": "tool_execution_failed",
        "http_status": 500,
        "recoverable": False,
        "message": "Tool execution failed",
    },
    # E9xx - Internal Errors
    ErrorCode.INTERNAL_ERROR: {
        "error": "internal_error",
        "http_status": 500,
        "recoverable": False,
        "message": "Internal server error",
    },
    ErrorCode.UNEXPECTED_EXCEPTION: {
        "error": "unexpected_exception",
        "http_status": 500,
        "recoverable": False,
        "message": "An unexpected error occurred",
    },
    ErrorCode.UNKNOWN_ERROR: {
        "error": "unknown_error",
        "http_status": 500,
        "recoverable": False,
        "message": "Unknown error",
    },
}


def get_error_http_status(code: ErrorCode) -> int:
    """Get the HTTP status code for an error code.

    Args:
        code: The error code to look up.

    Returns:
        HTTP status code (e.g., 400, 401, 500).

    Example:
        >>> get_error_http_status(ErrorCode.INVALID_API_KEY)
        401
    """
    status: int = ERROR_REGISTRY[code]["http_status"]
    return status


def create_error_response(
    code: ErrorCode,
    message: str | None = None,
    details: dict[str, Any] | None = None,
    retry_after: int | None = None,
) -> dict[str, Any]:
    """Create a standardized error response dictionary.

    Args:
        code: The error code from ErrorCode enum.
        message: Optional custom message (uses default if not provided).
        details: Optional additional context/details.
        retry_after: Optional seconds before client should retry (for recoverable errors).

    Returns:
        Dictionary with standardized error response fields:
        - code: Error code (E001-E999)
        - error: Error type identifier string
        - message: Human-readable description
        - recoverable: Whether client can retry
        - retry_after: Seconds before retry (if applicable)
        - details: Additional context (if provided)
        - timestamp: ISO 8601 timestamp

    Example:
        >>> response = create_error_response(
        ...     ErrorCode.SESSION_STORAGE_UNAVAILABLE,
        ...     retry_after=30,
        ... )
        >>> response["code"]
        'E110'
        >>> response["recoverable"]
        True
    """
    metadata = ERROR_REGISTRY[code]
    return {
        "code": code.value,
        "error": metadata["error"],
        "message": message or metadata["message"],
        "recoverable": metadata["recoverable"],
        "retry_after": retry_after,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
