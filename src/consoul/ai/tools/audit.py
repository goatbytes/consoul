"""Audit logging for tool execution tracking.

Provides pluggable audit logging infrastructure for tracking tool executions,
approval decisions, and results. Supports custom backends via AuditLogger protocol.

This module is SDK-ready and works without TUI dependencies.

Example (default file logger):
    >>> from consoul.ai.tools.audit import FileAuditLogger, AuditEvent
    >>> from pathlib import Path
    >>> logger = FileAuditLogger(Path.home() / ".consoul" / "audit.jsonl")
    >>> event = AuditEvent(
    ...     event_type="approval",
    ...     tool_name="bash_execute",
    ...     arguments={"command": "ls"},
    ...     decision=True
    ... )
    >>> await logger.log_event(event)

Example (custom logger):
    >>> class DatabaseAuditLogger:
    ...     async def log_event(self, event: AuditEvent) -> None:
    ...         await db.insert("audit_log", event.to_dict())
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["AuditEvent", "AuditLogger", "FileAuditLogger", "NullAuditLogger"]


@dataclass
class AuditEvent:
    """Structured audit event for tool execution tracking.

    Captures complete information about tool execution lifecycle including
    approval decisions, execution results, and errors.

    Attributes:
        timestamp: Event timestamp (UTC)
        event_type: Type of event (request/approval/denial/execution/result/error)
        tool_name: Name of tool being executed
        arguments: Tool arguments as dict
        user: Optional user identifier (for multi-tenant scenarios)
        decision: Approval decision (True=approved, False=denied, None=pending)
        result: Tool execution result (stdout/return value)
        duration_ms: Execution duration in milliseconds
        error: Error message if execution failed
        metadata: Additional context (session_id, host_app_id, etc.)

    Example:
        >>> event = AuditEvent(
        ...     event_type="approval",
        ...     tool_name="bash_execute",
        ...     arguments={"command": "git status"},
        ...     decision=True,
        ...     metadata={"user_id": "jared@goatbytes.io"}
        ... )
    """

    event_type: Literal[
        "request", "approval", "denial", "execution", "result", "error", "blocked"
    ]
    tool_name: str
    arguments: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user: str | None = None
    decision: bool | None = None
    result: str | None = None
    duration_ms: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization.

        Returns:
            Dictionary with all event fields, timestamp as ISO 8601 string.
        """
        data = asdict(self)
        # Convert datetime to ISO 8601 string
        data["timestamp"] = self.timestamp.isoformat()
        return data


class AuditLogger(Protocol):
    """Protocol for pluggable audit logging backends.

    Implement this protocol to create custom audit loggers (database,
    remote service, etc.) that can be injected into ToolRegistry.

    Example:
        >>> class RemoteAuditLogger:
        ...     async def log_event(self, event: AuditEvent) -> None:
        ...         async with httpx.AsyncClient() as client:
        ...             await client.post(
        ...                 "https://api.example.com/audit",
        ...                 json=event.to_dict()
        ...             )
    """

    async def log_event(self, event: AuditEvent) -> None:
        """Log an audit event.

        Args:
            event: AuditEvent to log

        Note:
            This method should not raise exceptions - log errors internally
            or silently fail to avoid disrupting tool execution.
        """
        ...


class FileAuditLogger:
    """File-based audit logger using JSONL format.

    Appends audit events as JSON objects (one per line) to a log file.
    JSONL format allows easy parsing with standard Unix tools (grep, tail, jq).

    The logger automatically creates the log directory if it doesn't exist
    and uses async I/O to avoid blocking tool execution.

    Example:
        >>> from pathlib import Path
        >>> logger = FileAuditLogger(Path.home() / ".consoul" / "audit.jsonl")
        >>> event = AuditEvent(
        ...     event_type="execution",
        ...     tool_name="bash_execute",
        ...     arguments={"command": "npm test"}
        ... )
        >>> await logger.log_event(event)

    Note:
        Uses append mode to ensure events are never lost, even if multiple
        processes are writing to the same file.
    """

    def __init__(self, log_file: Path) -> None:
        """Initialize file audit logger.

        Args:
            log_file: Path to JSONL audit log file
        """
        from pathlib import Path as _Path

        # Convert string to Path if needed
        self.log_file = _Path(log_file) if not isinstance(log_file, _Path) else log_file

    def _write_sync(self, event_json: str) -> None:
        """Synchronous write helper for executor.

        Args:
            event_json: JSON string to write to log file
        """
        # Ensure directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Append to file
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(event_json + "\n")

    async def log_event(self, event: AuditEvent) -> None:
        """Log event to JSONL file asynchronously to avoid blocking UI.

        Args:
            event: AuditEvent to log

        Note:
            Silently fails on errors to avoid disrupting tool execution.
            Errors are printed to stderr for debugging.
        """
        try:
            # Convert event to JSON
            event_json = json.dumps(event.to_dict())

            # Run blocking file I/O in executor to avoid blocking event loop
            import asyncio

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,  # Use default ThreadPoolExecutor
                self._write_sync,
                event_json,
            )

        except Exception as e:
            # Silently fail - don't disrupt tool execution
            # In production, could log to stderr or system logger
            import sys

            print(f"Audit logging error: {e}", file=sys.stderr)


class NullAuditLogger:
    """No-op audit logger for disabled audit logging.

    Provides zero-overhead logging when audit_logging=False in config.
    All log_event calls are no-ops.

    Example:
        >>> logger = NullAuditLogger()
        >>> await logger.log_event(event)  # Does nothing
    """

    async def log_event(self, event: AuditEvent) -> None:
        """No-op log event.

        Args:
            event: AuditEvent (ignored)
        """
        pass
