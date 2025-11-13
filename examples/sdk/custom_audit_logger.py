#!/usr/bin/env python3
"""Custom Audit Logger Examples.

Demonstrates implementing custom audit logging backends for compliance,
monitoring, and security requirements.

Includes implementations for:
- Database (SQLite/PostgreSQL)
- Cloud logging (structured JSON)
- Multi-backend composite logger

Usage:
    python examples/sdk/custom_audit_logger.py --demo sqlite
    python examples/sdk/custom_audit_logger.py --demo multi

Requirements:
    pip install consoul aiosqlite  # For SQLite example
    pip install asyncpg            # For PostgreSQL example
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from consoul.ai.tools.audit import AuditEvent, AuditLogger

# =============================================================================
# SQLite Audit Logger
# =============================================================================


class SQLiteAuditLogger:
    """Audit logger using SQLite database.

    Suitable for single-instance applications, local development,
    and embedded systems.

    Example:
        >>> logger = SQLiteAuditLogger("~/.consoul/audit.db")
        >>> registry = ToolRegistry(config, audit_logger=logger)
    """

    def __init__(self, database_path: str | Path):
        """Initialize SQLite audit logger.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    async def _init_database(self) -> None:
        """Create audit_log table if it doesn't exist."""
        try:
            import aiosqlite

            async with aiosqlite.connect(self.database_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        arguments TEXT,
                        user_id TEXT,
                        decision INTEGER,
                        result TEXT,
                        duration_ms INTEGER,
                        error TEXT,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_event_type ON audit_log(event_type)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tool_name ON audit_log(tool_name)"
                )
                await db.commit()
        except ImportError:
            print("Warning: aiosqlite not installed, audit logging disabled")
            print("Install with: pip install aiosqlite")
        except Exception as e:
            print(f"Warning: Could not initialize audit database: {e}")

    async def log_event(self, event: AuditEvent) -> None:
        """Log event to SQLite database.

        Args:
            event: AuditEvent to log
        """
        try:
            import aiosqlite

            # Initialize database if needed
            if not self.database_path.exists():
                await self._init_database()

            async with aiosqlite.connect(self.database_path) as db:
                await db.execute(
                    """
                    INSERT INTO audit_log (
                        timestamp, event_type, tool_name, arguments,
                        user_id, decision, result, duration_ms, error, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.timestamp.isoformat(),
                        event.event_type,
                        event.tool_name,
                        json.dumps(event.arguments),
                        event.user,
                        1
                        if event.decision
                        else (0 if event.decision is False else None),
                        event.result,
                        event.duration_ms,
                        event.error,
                        json.dumps(event.metadata),
                    ),
                )
                await db.commit()
        except ImportError:
            pass  # Silently skip if aiosqlite not available
        except Exception as e:
            # Don't break tool execution on audit failures
            import sys

            print(f"Audit logging error: {e}", file=sys.stderr)


# =============================================================================
# Cloud/Structured Logger
# =============================================================================


class StructuredAuditLogger:
    """Structured JSON logger for cloud logging services.

    Outputs structured JSON suitable for CloudWatch, Stackdriver,
    Splunk, or any log aggregation service.

    Example:
        >>> logger = StructuredAuditLogger("/var/log/consoul/audit.json")
        >>> registry = ToolRegistry(config, audit_logger=logger)
    """

    def __init__(self, log_path: str | Path):
        """Initialize structured logger.

        Args:
            log_path: Path to structured log file
        """
        self.log_path = Path(log_path).expanduser()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def log_event(self, event: AuditEvent) -> None:
        """Log event as structured JSON.

        Args:
            event: AuditEvent to log
        """
        try:
            # Build structured log entry
            log_entry = {
                "@timestamp": event.timestamp.isoformat(),
                "event": {
                    "type": event.event_type,
                    "category": "tool_execution",
                    "module": "consoul",
                },
                "tool": {
                    "name": event.tool_name,
                    "arguments": event.arguments,
                },
                "result": {
                    "decision": event.decision,
                    "output": event.result,
                    "duration_ms": event.duration_ms,
                    "error": event.error,
                },
                "user": {
                    "id": event.user,
                },
                "metadata": event.metadata,
            }

            # Async file write
            def write_log():
                with self.log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")

            await asyncio.to_thread(write_log)

        except Exception as e:
            import sys

            print(f"Audit logging error: {e}", file=sys.stderr)


# =============================================================================
# Multi-Backend Logger
# =============================================================================


class MultiAuditLogger:
    """Composite logger that writes to multiple backends simultaneously.

    Useful for:
    - Writing to both local file and database
    - Sending to both local and cloud logging
    - Implementing redundancy

    Example:
        >>> logger = MultiAuditLogger([
        ...     FileAuditLogger(Path("audit.jsonl")),
        ...     SQLiteAuditLogger(Path("audit.db")),
        ...     StructuredAuditLogger(Path("audit.json")),
        ... ])
    """

    def __init__(self, loggers: list[AuditLogger]):
        """Initialize multi-backend logger.

        Args:
            loggers: List of audit logger instances
        """
        self.loggers = loggers

    async def log_event(self, event: AuditEvent) -> None:
        """Log to all backends concurrently.

        Args:
            event: AuditEvent to log
        """
        # Log to all backends concurrently
        tasks = [logger.log_event(event) for logger in self.loggers]

        # Gather with return_exceptions to prevent one failure from breaking others
        await asyncio.gather(*tasks, return_exceptions=True)


# =============================================================================
# Demo and Testing
# =============================================================================


async def demo_sqlite_logger() -> None:
    """Demonstrate SQLite audit logger."""
    print("SQLite Audit Logger Demo")
    print("=" * 70)
    print()

    # Create logger
    log_path = Path.home() / ".consoul" / "demo_audit.db"
    logger = SQLiteAuditLogger(log_path)

    print(f"✓ Logger created: {log_path}")
    print()

    # Log some events
    events = [
        AuditEvent(
            event_type="request",
            tool_name="bash_execute",
            arguments={"command": "ls -la"},
            metadata={"user_id": "demo"},
        ),
        AuditEvent(
            event_type="approval",
            tool_name="bash_execute",
            arguments={"command": "ls -la"},
            decision=True,
            duration_ms=150,
            metadata={"user_id": "demo"},
        ),
        AuditEvent(
            event_type="execution",
            tool_name="bash_execute",
            arguments={"command": "ls -la"},
            metadata={"user_id": "demo"},
        ),
        AuditEvent(
            event_type="result",
            tool_name="bash_execute",
            arguments={"command": "ls -la"},
            result="total 48\ndrwxr-xr-x ...",
            duration_ms=50,
            metadata={"user_id": "demo"},
        ),
    ]

    print("Logging events...")
    for event in events:
        await logger.log_event(event)
        print(f"  ✓ {event.event_type}: {event.tool_name}")

    print()
    print(f"✓ Events logged to {log_path}")
    print()

    # Query events (requires aiosqlite)
    try:
        import aiosqlite

        async with aiosqlite.connect(log_path) as db:
            cursor = await db.execute(
                "SELECT event_type, tool_name, timestamp FROM audit_log ORDER BY id DESC LIMIT 5"
            )
            rows = await cursor.fetchall()

            print("Recent events:")
            for row in rows:
                print(f"  {row[0]}: {row[1]} at {row[2]}")
            print()

    except ImportError:
        print("Install aiosqlite to query database: pip install aiosqlite")


async def demo_multi_logger() -> None:
    """Demonstrate multi-backend logger."""
    print("Multi-Backend Audit Logger Demo")
    print("=" * 70)
    print()

    from consoul.ai.tools.audit import FileAuditLogger

    # Create multiple loggers
    loggers = [
        FileAuditLogger(Path.home() / ".consoul" / "demo_file.jsonl"),
        SQLiteAuditLogger(Path.home() / ".consoul" / "demo_multi.db"),
        StructuredAuditLogger(Path.home() / ".consoul" / "demo_structured.json"),
    ]

    multi_logger = MultiAuditLogger(loggers)

    print("✓ Multi-logger created with 3 backends:")
    print("  - JSONL file logger")
    print("  - SQLite database logger")
    print("  - Structured JSON logger")
    print()

    # Log event
    event = AuditEvent(
        event_type="approval",
        tool_name="bash_execute",
        arguments={"command": "git status"},
        decision=True,
        duration_ms=200,
        metadata={"user_id": "demo", "session": "multi-demo"},
    )

    print("Logging event to all backends...")
    await multi_logger.log_event(event)

    print("✓ Event logged to all backends")
    print()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Custom audit logger examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # SQLite logger demo
  %(prog)s --demo sqlite

  # Multi-backend logger demo
  %(prog)s --demo multi

  # Structured logger demo
  %(prog)s --demo structured
        """,
    )

    parser.add_argument(
        "--demo",
        choices=["sqlite", "multi", "structured"],
        help="Run demo",
    )

    args = parser.parse_args()

    if args.demo == "sqlite":
        asyncio.run(demo_sqlite_logger())
    elif args.demo == "multi":
        asyncio.run(demo_multi_logger())
    elif args.demo == "structured":
        print("Structured logger demo")
        print("(Same as multi-demo, check ~/.consoul/demo_structured.json)")
        asyncio.run(demo_multi_logger())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
