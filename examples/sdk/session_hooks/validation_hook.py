"""Validation hook for session state.

Validates session state before save to ensure data integrity.
Rejects saves that would create invalid state.

Example:
    >>> from examples.sdk.session_hooks import ValidationHook
    >>> from consoul.sdk import HookedSessionStore, MemorySessionStore
    >>>
    >>> hook = ValidationHook(
    ...     required_fields=["session_id", "messages"],
    ...     max_messages=1000,
    ... )
    >>> store = HookedSessionStore(
    ...     store=MemorySessionStore(),
    ...     hooks=[hook]
    ... )
"""

from __future__ import annotations

from typing import Any


class ValidationError(Exception):
    """Raised when session state validation fails."""

    pass


class ValidationHook:
    """Validates session state before storage.

    Performs schema and constraint validation to ensure only
    valid session states are persisted.

    Attributes:
        required_fields: Fields that must be present
        max_messages: Maximum allowed messages (None = no limit)
        max_message_length: Maximum content length per message
        allowed_roles: Valid message roles

    Example:
        >>> hook = ValidationHook(
        ...     required_fields=["session_id", "messages"],
        ...     max_messages=500,
        ...     max_message_length=100000,
        ... )
    """

    def __init__(
        self,
        required_fields: list[str] | None = None,
        max_messages: int | None = None,
        max_message_length: int | None = None,
        allowed_roles: list[str] | None = None,
    ) -> None:
        """Initialize validation hook.

        Args:
            required_fields: Fields that must be present in state
            max_messages: Maximum allowed messages (None = unlimited)
            max_message_length: Max chars per message content
            allowed_roles: Valid message roles (e.g., ["user", "assistant", "system"])
        """
        self.required_fields = set(required_fields or ["session_id", "messages"])
        self.max_messages = max_messages
        self.max_message_length = max_message_length
        self.allowed_roles = set(allowed_roles or [])

    def _validate_state(self, state: dict[str, Any]) -> None:
        """Validate state and raise ValidationError if invalid."""
        # Check required fields
        missing = self.required_fields - set(state.keys())
        if missing:
            raise ValidationError(f"Missing required fields: {missing}")

        # Validate messages
        messages = state.get("messages", [])

        if not isinstance(messages, list):
            raise ValidationError("messages must be a list")

        # Check message count
        if self.max_messages is not None and len(messages) > self.max_messages:
            raise ValidationError(
                f"Too many messages: {len(messages)} > {self.max_messages}"
            )

        # Validate each message
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValidationError(f"Message {i} must be a dict")

            # Check role if we have allowed_roles
            if self.allowed_roles:
                role = msg.get("role")
                if role not in self.allowed_roles:
                    raise ValidationError(
                        f"Invalid role '{role}' in message {i}. "
                        f"Allowed: {self.allowed_roles}"
                    )

            # Check content length
            if self.max_message_length is not None:
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > self.max_message_length:
                    raise ValidationError(
                        f"Message {i} content too long: "
                        f"{len(content)} > {self.max_message_length}"
                    )

    def on_before_save(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate state before saving.

        Args:
            session_id: Session identifier
            state: Session state dictionary

        Returns:
            Unmodified state if valid

        Raises:
            ValidationError: If state fails validation
        """
        self._validate_state(state)
        return state

    def on_after_load(
        self,
        session_id: str,
        state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """No-op for validation hook (validation happens on save).

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
        """No-op for validation hook.

        Args:
            session_id: Session identifier
            state: Session state dictionary
        """
        pass
