"""PII redaction hook for session state.

Redacts personally identifiable information (PII) from session messages
before storage. Uses pattern-based redaction for common PII formats.

Warning:
    Redaction is ONE-WAY - original data cannot be recovered.
    Use encryption instead if you need to preserve original content.

Example:
    >>> from examples.sdk.session_hooks import RedactionHook
    >>> from consoul.sdk import HookedSessionStore, MemorySessionStore
    >>>
    >>> hook = RedactionHook(
    ...     fields=["password", "api_key"],
    ...     patterns=True  # Enable SSN, credit card detection
    ... )
    >>> store = HookedSessionStore(
    ...     store=MemorySessionStore(),
    ...     hooks=[hook]
    ... )
"""

from __future__ import annotations

import re
from re import Pattern
from typing import Any, ClassVar


class RedactionHook:
    """Redacts PII from session messages before storage.

    Supports two modes of redaction:
    1. Field-based: Redact specific dict keys (e.g., "password", "ssn")
    2. Pattern-based: Detect and redact common PII patterns in text

    Attributes:
        fields: List of field names to redact
        patterns: Whether to enable pattern-based redaction
        replacement: Replacement string for redacted content

    Example:
        >>> hook = RedactionHook(
        ...     fields=["password", "credit_card", "ssn"],
        ...     patterns=True
        ... )
    """

    # Common PII patterns
    PATTERNS: ClassVar[dict[str, Pattern[str]]] = {
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "api_key": re.compile(
            r"\b(sk-|pk_|api[_-]?key[=:]?\s*)[a-zA-Z0-9]{20,}\b", re.I
        ),
    }

    def __init__(
        self,
        fields: list[str] | None = None,
        patterns: bool = True,
        replacement: str = "[REDACTED]",
    ) -> None:
        """Initialize redaction hook.

        Args:
            fields: Field names to redact (e.g., ["password", "ssn"])
            patterns: Enable pattern-based PII detection
            replacement: String to replace redacted content
        """
        self.fields = set(fields or [])
        self.patterns = patterns
        self.replacement = replacement

    def _redact_text(self, text: str) -> str:
        """Apply pattern-based redaction to text."""
        if not self.patterns:
            return text

        result = text
        for pattern in self.PATTERNS.values():
            result = pattern.sub(self.replacement, result)
        return result

    def _redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact fields in a dictionary."""
        result = {}
        for key, value in data.items():
            # Check if this field should be redacted
            if key.lower() in {f.lower() for f in self.fields}:
                result[key] = self.replacement
            elif isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._redact_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                result[key] = self._redact_text(value)
            else:
                result[key] = value
        return result

    def on_before_save(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Redact PII from session state before saving.

        Args:
            session_id: Session identifier (not used)
            state: Session state dictionary

        Returns:
            Redacted state dictionary
        """
        # Deep copy and redact messages
        result = state.copy()

        if "messages" in result:
            redacted_messages = []
            for msg in result["messages"]:
                if isinstance(msg, dict):
                    redacted_msg = self._redact_dict(msg)
                    # Also redact content field specifically
                    if "content" in redacted_msg and isinstance(
                        redacted_msg["content"], str
                    ):
                        redacted_msg["content"] = self._redact_text(
                            redacted_msg["content"]
                        )
                    redacted_messages.append(redacted_msg)
                else:
                    redacted_messages.append(msg)
            result["messages"] = redacted_messages

        return result

    def on_after_load(
        self,
        session_id: str,
        state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """No-op - redaction is one-way.

        Args:
            session_id: Session identifier
            state: Session state dictionary

        Returns:
            Unmodified state
        """
        return state

    def on_after_save(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> None:
        """No-op for redaction hook.

        Args:
            session_id: Session identifier
            state: Session state dictionary
        """
        pass
