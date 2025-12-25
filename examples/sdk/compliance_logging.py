"""Compliance Logging Example for Legal Tech Deployments.

Demonstrates structured JSON logging with correlation IDs, PII redaction,
and compliance audit trails for GDPR/HIPAA requirements.

This example shows how to:
1. Enable structured logging with LoggingConfig
2. Track requests with correlation IDs
3. Redact PII and secrets from logs
4. Query logs for compliance reports

Usage:
    python examples/sdk/compliance_logging.py

Requirements:
    pip install consoul[logging]

Output:
    Creates audit.jsonl with JSON-formatted compliance logs
    Shows example queries for audit trail analysis
"""

import asyncio
from pathlib import Path

from consoul.ai.tools.audit import AuditEvent, StructuredAuditLogger
from consoul.config import load_config
from consoul.config.models import LoggingConfig
from consoul.sdk.context import get_correlation_id, set_correlation_id
from consoul.sdk.services import ConversationService


async def main() -> None:
    """Run compliance logging demonstration."""

    # 1. Configure structured logging for compliance
    print("=== Configuring Compliance Logging ===\n")

    logging_config = LoggingConfig(
        enabled=True,
        format="json",
        output="file",
        file_path=Path("./audit.jsonl"),
        redact_pii=True,
        redact_fields=["password", "api_key", "token", "ssn"],
        max_arg_length=1000,
        correlation_ids=True,
    )

    print(f"Log format: {logging_config.format}")
    print(f"Output: {logging_config.file_path}")
    print(f"PII redaction: {logging_config.redact_pii}")
    print(f"Correlation IDs: {logging_config.correlation_ids}\n")

    # 2. Create structured audit logger
    audit_logger = StructuredAuditLogger(logging_config)

    # 3. Demonstrate correlation ID tracking
    print("=== Correlation ID Tracking ===\n")

    # Set correlation ID for request (auto-generated)
    correlation_id = set_correlation_id()
    print(f"Generated correlation ID: {correlation_id}")
    print(f"Retrieved from context: {get_correlation_id()}\n")

    # 4. Log sample compliance events
    print("=== Logging Sample Events ===\n")

    # Log user request
    await audit_logger.log_event(
        AuditEvent(
            event_type="request",
            tool_name="message",
            arguments={"query": "Analyze contract.pdf"},
            correlation_id=correlation_id,
            session_id="user-alice-123",
            user="alice@lawfirm.com",
            metadata={"document": "contract.pdf", "page_count": 42},
        )
    )
    print("✓ Logged user request")

    # Log tool execution with PII redaction
    await audit_logger.log_event(
        AuditEvent(
            event_type="execution",
            tool_name="bash_execute",
            arguments={
                "command": "export API_KEY=sk-abc123def456 && curl https://api.example.com"
            },
            result="Successfully retrieved data",
            duration_ms=450,
            correlation_id=correlation_id,
            session_id="user-alice-123",
            user="alice@lawfirm.com",
            decision=True,
            metadata={"risk_level": "caution", "approved_by": "alice@lawfirm.com"},
        )
    )
    print("✓ Logged tool execution (API key redacted)")

    # Log completion
    await audit_logger.log_event(
        AuditEvent(
            event_type="result",
            tool_name="message",
            arguments={},
            result="Analysis completed",
            duration_ms=5200,
            correlation_id=correlation_id,
            session_id="user-alice-123",
            metadata={"model": "claude-sonnet-4", "total_tokens": 1500},
        )
    )
    print("✓ Logged completion\n")

    # 5. Use with ConversationService
    print("=== Using with ConversationService ===\n")

    # Load config and enable logging
    config = load_config()
    config.logging = logging_config

    # Create service with structured logging
    service = ConversationService.from_config(config)

    # Set new correlation ID for this conversation
    conversation_id = set_correlation_id("chat-session-789")
    print(f"Conversation correlation ID: {conversation_id}\n")

    # Send message (will log request/response automatically)
    print("Sending message (logging enabled)...\n")
    async for token in service.send_message("What is the capital of France?"):
        print(token.content, end="", flush=True)

    print("\n\n=== Log File Contents ===\n")

    # Read and display audit log
    if logging_config.file_path.exists():
        with open(logging_config.file_path, encoding="utf-8") as f:
            for line in f:
                print(line.strip())
    else:
        print("No log file created yet")

    print("\n=== Compliance Query Examples ===\n")

    print("1. Find all actions by specific user:")
    print("   jq '.user == \"alice@lawfirm.com\"' audit.jsonl")
    print()

    print("2. Find all tool executions:")
    print("   jq 'select(.event_type == \"execution\")' audit.jsonl")
    print()

    print("3. Trace complete request by correlation ID:")
    print(f"   jq 'select(.correlation_id == \"{correlation_id}\")' audit.jsonl")
    print()

    print("4. Find all events for a session:")
    print("   jq 'select(.session_id == \"user-alice-123\")' audit.jsonl")
    print()

    print("5. Find errors in last hour:")
    print(
        '   jq \'select(.event_type == "error" and .timestamp > "'
        "TIMESTAMP_HERE\")' audit.jsonl"
    )
    print()

    print("6. Aggregate tool usage by user:")
    print("   jq 'group_by(.user) | map({user: .[0].user, count: length})' audit.jsonl")
    print()

    print("=== Compliance Report Example ===\n")

    print("Audit Trail Summary:")
    print(f"  - Correlation ID: {correlation_id}")
    print("  - User: alice@lawfirm.com")
    print("  - Session: user-alice-123")
    print("  - Events logged: 3")
    print("  - Duration: 5.2s")
    print("  - Tools used: bash_execute")
    print("  - PII redacted: ✓ (API keys, tokens)")
    print("  - Compliance: GDPR/HIPAA compatible")
    print()

    print("✓ Compliance logging demonstration complete!")
    print(f"✓ Audit log: {logging_config.file_path.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
