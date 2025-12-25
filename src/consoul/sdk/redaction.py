"""PII and secret redaction for compliance logging.

Provides field-based and pattern-based redaction of sensitive data before
logging to ensure compliance with data protection regulations (GDPR, HIPAA, etc.).

Supports:
- Field name redaction (password, api_key, token, etc.)
- Regex pattern matching (SSN, credit cards, JWT tokens)
- Configurable redaction markers
- Nested dictionary traversal

Example - Field redaction:
    >>> from consoul.sdk.redaction import PiiRedactor
    >>> redactor = PiiRedactor(fields=["password", "api_key"])
    >>> data = {"user": "alice", "password": "secret123", "message": "hello"}
    >>> redactor.redact_dict(data)
    {'user': 'alice', 'password': '[REDACTED]', 'message': 'hello'}

Example - Pattern matching:
    >>> data = {"message": "My SSN is 123-45-6789"}
    >>> redactor.redact_dict(data)
    {'message': 'My SSN is [REDACTED-SSN]'}

Example - Tool arguments:
    >>> args = {"command": "export API_KEY=sk-abc123def456"}
    >>> redactor.redact_dict(args)
    {'command': 'export API_KEY=[REDACTED-API_KEY]'}
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["DEFAULT_REDACT_FIELDS", "REDACTION_PATTERNS", "PiiRedactor"]

# Common PII/secret patterns (regex patterns for automatic detection)
REDACTION_PATTERNS: dict[str, str] = {
    "api_key": r"(sk-|pk-|key-)[a-zA-Z0-9]{20,}",
    "bearer_token": r"Bearer\s+[a-zA-Z0-9_\-\.]+",
    "jwt": r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "github_token": r"gh[ps]_[a-zA-Z0-9]{36,}",
}

# Default fields to redact (case-insensitive matching)
DEFAULT_REDACT_FIELDS: list[str] = [
    "password",
    "passwd",
    "pwd",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "auth",
    "authorization",
    "private_key",
    "privatekey",
    "session_key",
    "sessionkey",
]


class PiiRedactor:
    """Redacts PII and secrets from dictionaries before logging.

    Provides two-stage redaction:
    1. Field-based: Replace values of specified field names with [REDACTED]
    2. Pattern-based: Replace regex matches in string values with [REDACTED-{type}]

    Attributes:
        fields: List of field names to redact (case-insensitive)
        patterns: Dict of {name: regex_pattern} for pattern matching
        max_length: Maximum string length before truncation (0 = no limit)

    Example - Custom configuration:
        >>> redactor = PiiRedactor(
        ...     fields=["password", "ssn"],
        ...     patterns={"ssn": r"\\d{3}-\\d{2}-\\d{4}"},
        ...     max_length=1000
        ... )
        >>> data = {"password": "secret", "message": "SSN: 123-45-6789"}
        >>> redactor.redact_dict(data)
        {'password': '[REDACTED]', 'message': 'SSN: [REDACTED-SSN]'}
    """

    def __init__(
        self,
        fields: list[str] | None = None,
        patterns: dict[str, str] | None = None,
        max_length: int = 0,
    ) -> None:
        """Initialize PII redactor.

        Args:
            fields: List of field names to redact (default: DEFAULT_REDACT_FIELDS)
            patterns: Dict of {name: regex_pattern} (default: REDACTION_PATTERNS)
            max_length: Maximum string length before truncation (0 = no limit)
        """
        self.fields = {f.lower() for f in (fields or DEFAULT_REDACT_FIELDS)}
        self.patterns = patterns or REDACTION_PATTERNS
        self.max_length = max_length

        # Pre-compile regex patterns for performance
        self._compiled_patterns = {
            name: re.compile(pattern) for name, pattern in self.patterns.items()
        }

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive data from dictionary (creates new dict).

        Performs deep traversal of nested dictionaries and lists.
        Does not modify the original dictionary.

        Args:
            data: Dictionary potentially containing sensitive data

        Returns:
            New dictionary with sensitive data redacted

        Example:
            >>> data = {"user": {"name": "alice", "password": "secret"}}
            >>> redactor = PiiRedactor(fields=["password"])
            >>> redactor.redact_dict(data)
            {'user': {'name': 'alice', 'password': '[REDACTED]'}}
        """
        result = self._redact_value(data)
        if not isinstance(result, dict):
            raise TypeError(f"Expected dict, got {type(result)}")
        return result

    def _redact_value(self, value: Any, key: str | None = None) -> Any:
        """Recursively redact values based on type.

        Args:
            value: Value to redact (can be dict, list, str, or primitive)
            key: Optional field name for field-based redaction

        Returns:
            Redacted value (same type as input)
        """
        # Field-based redaction (check key name)
        if key and key.lower() in self.fields:
            return "[REDACTED]"

        # Recursive redaction for complex types
        if isinstance(value, dict):
            return {k: self._redact_value(v, k) for k, v in value.items()}

        if isinstance(value, list):
            return [self._redact_value(item) for item in value]

        if isinstance(value, str):
            # Pattern-based redaction
            redacted = value
            for pattern_name, compiled_pattern in self._compiled_patterns.items():
                if compiled_pattern.search(redacted):
                    redacted = compiled_pattern.sub(
                        f"[REDACTED-{pattern_name.upper()}]", redacted
                    )

            # Truncate long strings
            if self.max_length > 0 and len(redacted) > self.max_length:
                redacted = redacted[: self.max_length] + "...[TRUNCATED]"

            return redacted

        # Return primitives unchanged
        return value

    def redact_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Redact tool arguments (convenience method).

        Alias for redact_dict() with clearer semantics for tool arguments.

        Args:
            arguments: Tool arguments dictionary

        Returns:
            New dictionary with redacted arguments

        Example:
            >>> args = {"command": "curl -H 'Authorization: Bearer secret'"}
            >>> redactor = PiiRedactor()
            >>> redactor.redact_arguments(args)
            {'command': "curl -H 'Authorization: [REDACTED-BEARER_TOKEN]'"}
        """
        return self.redact_dict(arguments)

    def redact_result(self, result: str, max_length: int | None = None) -> str:
        """Redact tool result string.

        Args:
            result: Tool result string (stdout, return value, etc.)
            max_length: Optional max length override (uses self.max_length if None)

        Returns:
            Redacted result string

        Example:
            >>> result = "Password reset link: https://example.com?token=abc123"
            >>> redactor = PiiRedactor()
            >>> redactor.redact_result(result)
            'Password reset link: https://example.com?token=[REDACTED-JWT]'
        """
        # Apply pattern-based redaction
        redacted = result
        for pattern_name, compiled_pattern in self._compiled_patterns.items():
            if compiled_pattern.search(redacted):
                redacted = compiled_pattern.sub(
                    f"[REDACTED-{pattern_name.upper()}]", redacted
                )

        # Truncate if needed
        limit = max_length if max_length is not None else self.max_length
        if limit > 0 and len(redacted) > limit:
            redacted = redacted[:limit] + "...[TRUNCATED]"

        return redacted
