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

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "FileAuditLogger",
    "NullAuditLogger",
    "StructuredAuditLogger",
]


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
    correlation_id: str | None = None
    session_id: str | None = None
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

        Automatically injects correlation_id from context if not already set.

        Args:
            event: AuditEvent to log

        Note:
            Silently fails on errors to avoid disrupting tool execution.
            Errors are printed to stderr for debugging.
        """
        try:
            # Auto-inject correlation_id from context if not set
            if event.correlation_id is None:
                try:
                    from consoul.sdk.context import get_correlation_id

                    event.correlation_id = get_correlation_id()
                except ImportError:
                    # context module not available (structlog not installed)
                    pass

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


class StructuredAuditLogger:
    """Audit logger with PII redaction and configurable output destinations.

    Supports multiple output modes:
    - stdout: Log to standard output (for containers/log aggregators)
    - file: Log to file (traditional logging)
    - both: Log to both stdout and file

    Features:
    - Automatic PII/secret redaction before logging
    - Configurable via LoggingConfig
    - Correlation ID injection from context
    - Argument/result truncation for performance

    Example - File output with redaction:
        >>> from consoul.config.models import LoggingConfig
        >>> from pathlib import Path
        >>> config = LoggingConfig(
        ...     output="file",
        ...     file_path=Path("audit.jsonl"),
        ...     redact_pii=True,
        ...     redact_fields=["password", "api_key"],
        ...     max_arg_length=1000
        ... )
        >>> logger = StructuredAuditLogger(config)
        >>> event = AuditEvent(
        ...     event_type="execution",
        ...     tool_name="bash_execute",
        ...     arguments={"command": "echo $API_KEY"},
        ...     session_id="user-123"
        ... )
        >>> await logger.log_event(event)  # API_KEY redacted

    Example - Stdout output (containers):
        >>> config = LoggingConfig(output="stdout", format="json")
        >>> logger = StructuredAuditLogger(config)
        >>> await logger.log_event(event)  # Logs to stdout as JSON
    """

    def __init__(self, config: Any) -> None:
        """Initialize structured audit logger.

        Args:
            config: LoggingConfig instance with redaction and output settings
        """
        from pathlib import Path

        self.config = config
        self.output = config.output

        # Initialize file logger if needed
        self.file_logger = None
        if self.output in ("file", "both"):
            log_path = config.file_path
            if not log_path:
                log_path = Path.home() / ".consoul" / "logs" / "audit.jsonl"
            self.file_logger = FileAuditLogger(log_path)

        # Initialize redactor if PII redaction is enabled
        self.redactor = None
        if config.redact_pii:
            try:
                from consoul.sdk.redaction import REDACTION_PATTERNS, PiiRedactor

                # Pass both fields and default patterns to enable both field-based
                # and pattern-based redaction. Without explicit patterns, PiiRedactor
                # operates in field-only mode when fields is provided.
                self.redactor = PiiRedactor(
                    fields=config.redact_fields,
                    patterns=REDACTION_PATTERNS,
                    max_length=config.max_arg_length,
                )
            except ImportError:
                # redaction module not available (logging extra not installed)
                import warnings

                warnings.warn(
                    "PII redaction requested but consoul[logging] extra not installed. "
                    "Install with: pip install consoul[logging]",
                    UserWarning,
                    stacklevel=2,
                )

    async def log_event(self, event: AuditEvent) -> None:
        """Log event with PII redaction to configured output(s).

        Args:
            event: AuditEvent to log (will be redacted if config.redact_pii=True)
        """
        # Apply redaction if enabled
        if self.redactor:
            # Redact arguments
            event.arguments = self.redactor.redact_dict(event.arguments)

            # Redact result
            if event.result:
                event.result = self.redactor.redact_result(
                    event.result, max_length=self.config.max_arg_length
                )

            # Redact error message
            if event.error:
                event.error = self.redactor.redact_result(event.error, max_length=None)

            # Redact metadata
            event.metadata = self.redactor.redact_dict(event.metadata)

        # Auto-inject correlation_id from context if not set
        if event.correlation_id is None:
            try:
                from consoul.sdk.context import get_correlation_id

                event.correlation_id = get_correlation_id()
            except ImportError:
                # context module not available
                pass

        # Convert to JSON
        event_json = json.dumps(event.to_dict())

        # Write to stdout if configured
        if self.output in ("stdout", "both"):
            import sys

            print(event_json, file=sys.stdout, flush=True)

        # Write to file if configured
        if self.output in ("file", "both") and self.file_logger:
            # Use file logger's write mechanism
            import asyncio

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.file_logger._write_sync,
                event_json,
            )


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
