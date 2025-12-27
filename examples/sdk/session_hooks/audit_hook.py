"""Audit logging hook for session operations.

Logs session save/load operations for compliance audit trails.
Useful for GDPR, HIPAA, SOC 2, and other regulatory requirements.

Example:
    >>> import logging
    >>> from examples.sdk.session_hooks import AuditHook
    >>> from consoul.sdk import HookedSessionStore, MemorySessionStore
    >>>
    >>> # Configure audit logger
    >>> audit_logger = logging.getLogger("session_audit")
    >>> audit_logger.setLevel(logging.INFO)
    >>> handler = logging.FileHandler("audit.log")
    >>> audit_logger.addHandler(handler)
    >>>
    >>> # Create hook with logger
    >>> hook = AuditHook(logger=audit_logger)
    >>> store = HookedSessionStore(
    ...     store=MemorySessionStore(),
    ...     hooks=[hook]
    ... )
"""

from __future__ import annotations

import json
import logging
from typing import Any


class AuditHook:
    """Logs session save/load operations for compliance audit trails.

    Creates structured JSON log entries for each session operation,
    including timestamps, session IDs, and operation metadata.

    Attributes:
        logger: Python logger instance for audit output
        include_message_count: Include message count in logs
        include_model: Include model name in logs

    Log Entry Format:
        {
            "timestamp": "2025-12-26T10:30:00Z",
            "event": "session_save",
            "session_id": "user123:conv456",
            "message_count": 15,
            "model": "gpt-4o",
            "metadata": {"user_id": "user123"}
        }
    """

    def __init__(
        self,
        logger: logging.Logger | None = None,
        include_message_count: bool = True,
        include_model: bool = True,
    ) -> None:
        """Initialize audit hook.

        Args:
            logger: Logger instance (uses module logger if None)
            include_message_count: Include message count in logs
            include_model: Include model name in logs
        """
        self.logger = logger or logging.getLogger(__name__)
        self.include_message_count = include_message_count
        self.include_model = include_model

    def _format_timestamp(self) -> str:
        """Get ISO 8601 formatted timestamp."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def _create_log_entry(
        self,
        event: str,
        session_id: str,
        state: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create structured log entry.

        Args:
            event: Event type (session_save, session_load, etc.)
            session_id: Session identifier
            state: Session state (optional)
            extra: Additional fields to include

        Returns:
            Structured log entry dictionary
        """
        entry: dict[str, Any] = {
            "timestamp": self._format_timestamp(),
            "event": event,
            "session_id": session_id,
        }

        if state:
            if self.include_message_count and "messages" in state:
                entry["message_count"] = len(state["messages"])

            if self.include_model and "model" in state:
                entry["model"] = state["model"]

            # Include metadata if present (user_id, tenant_id, etc.)
            if state.get("metadata"):
                metadata = state["metadata"]
                if isinstance(metadata, dict):
                    # Only include safe fields
                    safe_fields = ["user_id", "tenant_id", "namespace", "tags"]
                    entry["metadata"] = {
                        k: v for k, v in metadata.items() if k in safe_fields
                    }

        if extra:
            entry.update(extra)

        return entry

    def on_before_save(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Pass through - audit happens after save.

        Args:
            session_id: Session identifier
            state: Session state dictionary

        Returns:
            Unmodified state
        """
        return state

    def on_after_load(
        self,
        session_id: str,
        state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Log session load operation.

        Args:
            session_id: Session identifier
            state: Session state dictionary or None

        Returns:
            Unmodified state
        """
        entry = self._create_log_entry(
            event="session_load",
            session_id=session_id,
            state=state,
            extra={"found": state is not None},
        )
        self.logger.info(json.dumps(entry))
        return state

    def on_after_save(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> None:
        """Log session save operation.

        Args:
            session_id: Session identifier
            state: Session state dictionary
        """
        entry = self._create_log_entry(
            event="session_save",
            session_id=session_id,
            state=state,
        )
        self.logger.info(json.dumps(entry))
