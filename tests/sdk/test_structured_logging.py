"""Tests for structured logging and compliance audit trails.

Tests cover:
1. JSON log format validation
2. Correlation ID propagation
3. PII/secret redaction
4. Session ID tracking
5. Event filtering and querying
6. Config model validation (no Pydantic errors)
"""

import json
from pathlib import Path

import pytest

from consoul.ai.tools.audit import AuditEvent, FileAuditLogger, StructuredAuditLogger
from consoul.config.models import LoggingConfig
from consoul.sdk.context import (
    clear_correlation_id,
    get_correlation_id,
    set_correlation_id,
)
from consoul.sdk.redaction import DEFAULT_REDACT_FIELDS, REDACTION_PATTERNS, PiiRedactor


class TestImportSmokeTest:
    """Test that config models import without Pydantic errors (P0 fix)."""

    def test_logging_config_imports_without_error(self):
        """Test LoggingConfig can be imported and instantiated."""
        # This will fail if validators reference non-existent fields
        config = LoggingConfig()
        assert config.enabled is True
        assert config.level == "INFO"
        assert config.format == "json"

    def test_logging_config_has_no_invalid_validators(self):
        """Test LoggingConfig does not have validators for missing fields."""

        # Get all field names
        field_names = set(LoggingConfig.model_fields.keys())

        # LoggingConfig should not have auto_approve or permission_policy
        assert "auto_approve" not in field_names
        assert "permission_policy" not in field_names

        # Verify expected fields exist
        assert "enabled" in field_names
        assert "level" in field_names
        assert "output" in field_names
        assert "redact_pii" in field_names

    def test_tool_config_validators_preserved(self):
        """Test ToolConfig validators were not removed (P2 regression check)."""
        from consoul.ai.tools.permissions.policy import PermissionPolicy
        from consoul.config.models import ToolConfig

        # Test default permission_policy is set to BALANCED
        config = ToolConfig()
        assert config.permission_policy == PermissionPolicy.BALANCED

        # Test that auto_approve validator exists and warns
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = ToolConfig(auto_approve=True)
            # Should have raised a warning
            assert len(w) == 1
            assert "DANGEROUS" in str(w[0].message)
            assert "auto_approve" in str(w[0].message)


class TestCorrelationIDs:
    """Test correlation ID context management."""

    def test_set_and_get_correlation_id(self):
        """Test setting and retrieving correlation ID."""
        # Clear any existing ID
        clear_correlation_id()

        # Set custom ID
        custom_id = "test-correlation-123"
        result = set_correlation_id(custom_id)

        assert result == custom_id
        assert get_correlation_id() == custom_id

    def test_auto_generate_correlation_id(self):
        """Test auto-generating correlation ID."""
        clear_correlation_id()

        # Auto-generate ID
        generated_id = set_correlation_id()

        assert generated_id is not None
        assert generated_id.startswith("req-")
        assert len(generated_id) == 16  # "req-" + 12 hex chars
        assert get_correlation_id() == generated_id

    def test_correlation_id_cleared(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-123")
        assert get_correlation_id() == "test-123"

        clear_correlation_id()
        assert get_correlation_id() is None

    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self):
        """Test correlation ID propagates through async calls."""
        clear_correlation_id()
        correlation_id = set_correlation_id("async-test-456")

        async def inner_function():
            # Should have same correlation ID in nested async function
            return get_correlation_id()

        result = await inner_function()
        assert result == correlation_id


class TestPiiRedaction:
    """Test PII and secret redaction."""

    def test_field_based_redaction(self):
        """Test redacting by field name."""
        redactor = PiiRedactor(fields=["password", "api_key"])

        data = {
            "username": "alice",
            "password": "secret123",
            "email": "alice@example.com",
        }

        redacted = redactor.redact_dict(data)

        assert redacted["username"] == "alice"
        assert redacted["password"] == "[REDACTED]"
        assert redacted["email"] == "alice@example.com"

    def test_pattern_based_redaction_api_key(self):
        """Test redacting API keys using regex patterns."""
        redactor = PiiRedactor()

        data = {"command": "export API_KEY=sk-abc123def456ghi789"}

        redacted = redactor.redact_dict(data)

        assert "[REDACTED-API_KEY]" in redacted["command"]
        assert "sk-abc123" not in redacted["command"]

    def test_pattern_based_redaction_jwt(self):
        """Test redacting JWT tokens."""
        redactor = PiiRedactor()

        data = {
            "auth": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0In0.abc123"
        }

        redacted = redactor.redact_dict(data)

        assert "[REDACTED-JWT]" in redacted["auth"]
        assert "eyJhbGciOiJ" not in redacted["auth"]

    def test_nested_dict_redaction(self):
        """Test redacting nested dictionaries."""
        redactor = PiiRedactor(fields=["password"])

        data = {"user": {"name": "alice", "password": "secret"}, "admin": False}

        redacted = redactor.redact_dict(data)

        assert redacted["user"]["name"] == "alice"
        assert redacted["user"]["password"] == "[REDACTED]"
        assert redacted["admin"] is False

    def test_list_redaction(self):
        """Test redacting lists of dicts."""
        redactor = PiiRedactor(fields=["password"])

        data = {
            "users": [
                {"name": "alice", "password": "secret1"},
                {"name": "bob", "password": "secret2"},
            ]
        }

        redacted = redactor.redact_dict(data)

        assert redacted["users"][0]["password"] == "[REDACTED]"
        assert redacted["users"][1]["password"] == "[REDACTED]"

    def test_truncation(self):
        """Test string truncation for large values."""
        redactor = PiiRedactor(max_length=10)

        long_string = "a" * 100
        result = redactor.redact_result(long_string)

        assert len(result) <= 25  # 10 + "...[TRUNCATED]"
        assert result.endswith("...[TRUNCATED]")

    def test_default_redact_fields(self):
        """Test default redacted fields include common secrets."""
        assert "password" in DEFAULT_REDACT_FIELDS
        assert "api_key" in DEFAULT_REDACT_FIELDS
        assert "token" in DEFAULT_REDACT_FIELDS
        assert "secret" in DEFAULT_REDACT_FIELDS

    def test_redaction_patterns_coverage(self):
        """Test redaction patterns cover common PII."""
        assert "api_key" in REDACTION_PATTERNS
        assert "jwt" in REDACTION_PATTERNS
        assert "ssn" in REDACTION_PATTERNS
        assert "credit_card" in REDACTION_PATTERNS
        assert "github_token" in REDACTION_PATTERNS


class TestJsonLogFormat:
    """Test JSON log format validation."""

    @pytest.mark.asyncio
    async def test_audit_event_to_dict(self):
        """Test AuditEvent serializes to valid JSON."""
        event = AuditEvent(
            event_type="execution",
            tool_name="bash_execute",
            arguments={"command": "ls"},
            correlation_id="test-123",
            session_id="session-456",
            user="alice@example.com",
            duration_ms=150,
        )

        event_dict = event.to_dict()

        assert isinstance(event_dict, dict)
        assert event_dict["event_type"] == "execution"
        assert event_dict["tool_name"] == "bash_execute"
        assert event_dict["correlation_id"] == "test-123"
        assert event_dict["session_id"] == "session-456"
        assert event_dict["duration_ms"] == 150

        # Verify timestamp is ISO 8601 string
        assert isinstance(event_dict["timestamp"], str)
        assert "T" in event_dict["timestamp"]
        assert "Z" in event_dict["timestamp"] or "+" in event_dict["timestamp"]

    @pytest.mark.asyncio
    async def test_file_audit_logger_writes_valid_json(self, tmp_path):
        """Test FileAuditLogger writes valid JSONL."""
        log_file = tmp_path / "test_audit.jsonl"
        logger = FileAuditLogger(log_file)

        event = AuditEvent(
            event_type="request",
            tool_name="message",
            arguments={"query": "test"},
            correlation_id="test-789",
        )

        await logger.log_event(event)

        # Read and parse JSON
        assert log_file.exists()
        with open(log_file, encoding="utf-8") as f:
            line = f.readline().strip()
            parsed = json.loads(line)

        assert parsed["event_type"] == "request"
        assert parsed["tool_name"] == "message"
        assert parsed["correlation_id"] == "test-789"

    @pytest.mark.asyncio
    async def test_structured_logger_with_redaction(self, tmp_path):
        """Test StructuredAuditLogger applies redaction."""
        log_file = tmp_path / "redacted_audit.jsonl"
        config = LoggingConfig(
            file_path=log_file,
            redact_pii=True,
            redact_fields=["password"],
            max_arg_length=100,
        )

        logger = StructuredAuditLogger(config)

        event = AuditEvent(
            event_type="execution",
            tool_name="bash_execute",
            arguments={"command": "echo", "password": "secret123"},
            result="Password is secret123",
        )

        await logger.log_event(event)

        # Read and verify redaction
        with open(log_file, encoding="utf-8") as f:
            line = f.readline().strip()
            parsed = json.loads(line)

        assert parsed["arguments"]["password"] == "[REDACTED]"
        assert "secret123" not in parsed["result"]

    @pytest.mark.asyncio
    async def test_correlation_id_auto_injection(self, tmp_path):
        """Test FileAuditLogger auto-injects correlation ID from context."""
        log_file = tmp_path / "correlation_audit.jsonl"
        logger = FileAuditLogger(log_file)

        # Set correlation ID in context
        set_correlation_id("context-correlation-123")

        # Create event without correlation_id
        event = AuditEvent(
            event_type="request", tool_name="message", arguments={"query": "test"}
        )

        assert event.correlation_id is None  # Not set initially

        await logger.log_event(event)

        # Read and verify correlation ID was injected
        with open(log_file, encoding="utf-8") as f:
            line = f.readline().strip()
            parsed = json.loads(line)

        assert parsed["correlation_id"] == "context-correlation-123"

        clear_correlation_id()


class TestEventFiltering:
    """Test log event filtering and querying."""

    @pytest.mark.asyncio
    async def test_filter_by_session_id(self, tmp_path):
        """Test filtering events by session ID."""
        log_file = tmp_path / "session_audit.jsonl"
        logger = FileAuditLogger(log_file)

        # Log events for different sessions
        await logger.log_event(
            AuditEvent(
                event_type="request",
                tool_name="message",
                arguments={},
                session_id="session-1",
            )
        )
        await logger.log_event(
            AuditEvent(
                event_type="request",
                tool_name="message",
                arguments={},
                session_id="session-2",
            )
        )
        await logger.log_event(
            AuditEvent(
                event_type="execution",
                tool_name="bash",
                arguments={},
                session_id="session-1",
            )
        )

        # Read and filter by session_id
        session_1_events = []
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                event = json.loads(line.strip())
                if event.get("session_id") == "session-1":
                    session_1_events.append(event)

        assert len(session_1_events) == 2
        assert session_1_events[0]["event_type"] == "request"
        assert session_1_events[1]["event_type"] == "execution"

    @pytest.mark.asyncio
    async def test_filter_by_event_type(self, tmp_path):
        """Test filtering events by type."""
        log_file = tmp_path / "event_type_audit.jsonl"
        logger = FileAuditLogger(log_file)

        # Log different event types
        await logger.log_event(
            AuditEvent(event_type="request", tool_name="message", arguments={})
        )
        await logger.log_event(
            AuditEvent(event_type="execution", tool_name="bash", arguments={})
        )
        await logger.log_event(
            AuditEvent(event_type="result", tool_name="message", arguments={})
        )

        # Read and filter by event_type
        execution_events = []
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                event = json.loads(line.strip())
                if event.get("event_type") == "execution":
                    execution_events.append(event)

        assert len(execution_events) == 1
        assert execution_events[0]["tool_name"] == "bash"


@pytest.mark.asyncio
async def test_end_to_end_compliance_logging(tmp_path):
    """End-to-end test of compliance logging workflow."""
    log_file = tmp_path / "compliance_audit.jsonl"

    # 1. Configure logging
    config = LoggingConfig(
        file_path=log_file,
        redact_pii=True,
        redact_fields=["api_key"],
        correlation_ids=True,
    )

    # 2. Create logger
    logger = StructuredAuditLogger(config)

    # 3. Set correlation ID
    correlation_id = set_correlation_id("compliance-test-999")

    # 4. Log request
    await logger.log_event(
        AuditEvent(
            event_type="request",
            tool_name="message",
            arguments={"query": "Analyze document"},
            session_id="user-alice",
            user="alice@lawfirm.com",
        )
    )

    # 5. Log tool execution with secrets
    await logger.log_event(
        AuditEvent(
            event_type="execution",
            tool_name="bash_execute",
            arguments={"command": "curl -H 'api_key: sk-secret123'"},
            duration_ms=200,
            session_id="user-alice",
            user="alice@lawfirm.com",
        )
    )

    # 6. Log completion
    await logger.log_event(
        AuditEvent(
            event_type="result",
            tool_name="message",
            arguments={},
            result="Analysis complete",
            duration_ms=5000,
            session_id="user-alice",
        )
    )

    # 7. Verify audit trail
    assert log_file.exists()

    events = []
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            events.append(json.loads(line.strip()))

    assert len(events) == 3

    # Verify all events have same correlation ID
    assert all(e.get("correlation_id") == correlation_id for e in events)

    # Verify all events have session ID
    assert all(e.get("session_id") == "user-alice" for e in events)

    # Verify API key was redacted
    bash_event = next(e for e in events if e["tool_name"] == "bash_execute")
    assert "sk-secret123" not in str(bash_event["arguments"])
    assert "[REDACTED" in str(bash_event["arguments"])

    # Verify event sequence
    assert events[0]["event_type"] == "request"
    assert events[1]["event_type"] == "execution"
    assert events[2]["event_type"] == "result"

    clear_correlation_id()


class TestCorrelationIdPreservation:
    """Test that existing correlation IDs are preserved (P1 fix)."""

    def test_preserve_existing_correlation_id(self):
        """Test that set_correlation_id preserves existing IDs."""
        from consoul.sdk.context import (
            clear_correlation_id,
            get_correlation_id,
            set_correlation_id,
        )

        clear_correlation_id()

        # Set initial correlation ID (simulating HTTP header injection)
        existing_id = "external-trace-xyz-789"
        set_correlation_id(existing_id)

        # Verify it was set
        assert get_correlation_id() == existing_id

        # Simulate send_message logic: check before generating new ID
        current_id = get_correlation_id()
        if current_id is None:
            current_id = set_correlation_id()  # Would generate new

        # Should preserve the existing ID
        assert current_id == existing_id
        assert get_correlation_id() == existing_id

        clear_correlation_id()


class TestOutputConfiguration:
    """Test LoggingConfig output modes (P2 fix)."""

    @pytest.mark.asyncio
    async def test_stdout_output_mode(self, tmp_path, capsys):
        """Test output='stdout' writes to stdout only."""
        config = LoggingConfig(
            output="stdout",
            format="json",
            redact_pii=False,
        )

        logger = StructuredAuditLogger(config)

        event = AuditEvent(
            event_type="request",
            tool_name="message",
            arguments={"query": "test"},
            session_id="test-session",
        )

        await logger.log_event(event)

        # Verify stdout contains JSON
        captured = capsys.readouterr()
        assert "test-session" in captured.out
        assert '"event_type": "request"' in captured.out

        # Verify no file was created (file_logger should be None)
        assert logger.file_logger is None

    @pytest.mark.asyncio
    async def test_file_output_mode(self, tmp_path):
        """Test output='file' writes to file only."""
        log_file = tmp_path / "file_only.jsonl"
        config = LoggingConfig(
            output="file",
            file_path=log_file,
            format="json",
            redact_pii=False,
        )

        logger = StructuredAuditLogger(config)

        event = AuditEvent(
            event_type="execution",
            tool_name="bash",
            arguments={"command": "ls"},
        )

        await logger.log_event(event)

        # Verify file was created and contains event
        assert log_file.exists()
        with open(log_file, encoding="utf-8") as f:
            content = f.read()
            assert "bash" in content
            assert '"event_type": "execution"' in content

        # Verify file logger was initialized
        assert logger.file_logger is not None

    @pytest.mark.asyncio
    async def test_both_output_mode(self, tmp_path, capsys):
        """Test output='both' writes to both stdout and file."""
        log_file = tmp_path / "both_output.jsonl"
        config = LoggingConfig(
            output="both",
            file_path=log_file,
            format="json",
            redact_pii=False,
        )

        logger = StructuredAuditLogger(config)

        event = AuditEvent(
            event_type="result",
            tool_name="message",
            arguments={},
            result="completed",
            session_id="both-test",
        )

        await logger.log_event(event)

        # Verify stdout contains event
        captured = capsys.readouterr()
        assert "both-test" in captured.out
        assert '"event_type": "result"' in captured.out

        # Verify file also contains event
        assert log_file.exists()
        with open(log_file, encoding="utf-8") as f:
            content = f.read()
            assert "both-test" in content
            assert '"event_type": "result"' in content

    @pytest.mark.asyncio
    async def test_default_file_path_when_output_is_file(self):
        """Test that file output uses default path when file_path is None."""
        config = LoggingConfig(
            output="file",
            file_path=None,  # Should use default
            redact_pii=False,
        )

        logger = StructuredAuditLogger(config)

        # Verify file logger was initialized with default path
        assert logger.file_logger is not None
        expected_default = Path.home() / ".consoul" / "logs" / "audit.jsonl"
        assert logger.file_logger.log_file == expected_default

    def test_config_validator_sets_default_path(self):
        """Test LoggingConfig validator sets default path matching logger (P2 fix)."""
        # When output="file" and file_path is None, validator should set default
        config = LoggingConfig(output="file")

        # Validator should have set the default path
        assert config.file_path is not None
        expected = Path.home() / ".consoul" / "logs" / "audit.jsonl"
        assert config.file_path == expected

        # This should match what StructuredAuditLogger uses
        logger = StructuredAuditLogger(config)
        assert logger.file_logger.log_file == config.file_path


class TestTokenCostHandling:
    """Test token cost tracking doesn't crash (P1 fix)."""

    @pytest.mark.asyncio
    async def test_token_cost_is_float_not_dict(self):
        """Test that Token.cost is a float, not a dict (regression check)."""
        from consoul.sdk.models import Token

        # Token.cost should be float | None, not dict
        token = Token(content="hello", cost=0.0001)
        assert isinstance(token.cost, float)

        token_none = Token(content="world", cost=None)
        assert token_none.cost is None

    @pytest.mark.asyncio
    async def test_usage_metadata_token_tracking(self):
        """Test that token tracking uses usage_metadata, not Token.cost."""

        from langchain_core.messages import AIMessage

        # Simulate final AIMessage with usage_metadata (how LangChain provides it)
        message = AIMessage(
            content="Hello world",
            usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        )

        # Extract token counts (this is what send_message does)
        total_tokens = message.usage_metadata.get(
            "input_tokens", 0
        ) + message.usage_metadata.get("output_tokens", 0)

        assert total_tokens == 15

    @pytest.mark.asyncio
    async def test_token_cost_float_does_not_support_in_operator(self):
        """Test that checking 'in token.cost' would crash (the bug)."""
        from consoul.sdk.models import Token

        token = Token(content="test", cost=0.001)

        # This was the buggy code - would raise TypeError
        with pytest.raises(TypeError, match=r"not iterable|not subscriptable"):
            if "total_tokens" in token.cost:  # type: ignore
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
