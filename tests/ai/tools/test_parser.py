"""Tests for tool call parser module."""

from unittest.mock import MagicMock

import pytest

from consoul.ai.tools.parser import ParsedToolCall, has_tool_calls, parse_tool_calls


def create_mock_message(tool_calls: list[dict] | None = None) -> MagicMock:
    """Create a mock AIMessage with tool_calls.

    Args:
        tool_calls: List of tool call dicts, or None for no tool calls

    Returns:
        Mock AIMessage object
    """
    message = MagicMock()
    if tool_calls is not None:
        message.tool_calls = tool_calls
    else:
        # Simulate message without tool_calls attribute
        delattr(message, "tool_calls")
    return message


class TestParsedToolCall:
    """Tests for ParsedToolCall dataclass."""

    def test_parsed_tool_call_creation(self):
        """Test creating a ParsedToolCall instance."""
        tool_call = ParsedToolCall(
            id="call_123",
            name="bash_execute",
            arguments={"command": "ls -la"},
            raw={
                "id": "call_123",
                "name": "bash_execute",
                "args": {"command": "ls -la"},
            },
        )

        assert tool_call.id == "call_123"
        assert tool_call.name == "bash_execute"
        assert tool_call.arguments == {"command": "ls -la"}
        assert tool_call.raw["id"] == "call_123"

    def test_parsed_tool_call_repr(self):
        """Test string representation of ParsedToolCall."""
        tool_call = ParsedToolCall(
            id="call_123",
            name="test_tool",
            arguments={"arg1": "value1"},
            raw={},
        )

        repr_str = repr(tool_call)
        assert "call_123" in repr_str
        assert "test_tool" in repr_str

    def test_parsed_tool_call_repr_long_args(self):
        """Test repr truncates long arguments."""
        long_args = {f"arg{i}": f"value{i}" for i in range(20)}
        tool_call = ParsedToolCall(
            id="call_123",
            name="test_tool",
            arguments=long_args,
            raw={},
        )

        repr_str = repr(tool_call)
        assert "..." in repr_str  # Should truncate long args


class TestParseToolCalls:
    """Tests for parse_tool_calls function."""

    def test_parse_single_tool_call(self):
        """Test parsing a single valid tool call."""
        message = create_mock_message(
            [
                {
                    "id": "call_abc123",
                    "name": "bash_execute",
                    "args": {"command": "ls -la"},
                }
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].id == "call_abc123"
        assert parsed[0].name == "bash_execute"
        assert parsed[0].arguments == {"command": "ls -la"}

    def test_parse_multiple_tool_calls(self):
        """Test parsing multiple parallel tool calls."""
        message = create_mock_message(
            [
                {
                    "id": "call_1",
                    "name": "bash_execute",
                    "args": {"command": "ls"},
                },
                {
                    "id": "call_2",
                    "name": "bash_execute",
                    "args": {"command": "pwd"},
                },
                {
                    "id": "call_3",
                    "name": "python_execute",
                    "args": {"code": "print('hello')"},
                },
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 3
        assert parsed[0].name == "bash_execute"
        assert parsed[1].name == "bash_execute"
        assert parsed[2].name == "python_execute"
        assert parsed[0].arguments["command"] == "ls"
        assert parsed[1].arguments["command"] == "pwd"

    def test_parse_tool_call_with_call_id_field(self):
        """Test parsing tool call using 'call_id' instead of 'id'."""
        message = create_mock_message(
            [
                {
                    "call_id": "call_xyz789",
                    "name": "bash_execute",
                    "args": {"command": "echo test"},
                }
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].id == "call_xyz789"

    def test_parse_tool_call_with_arguments_field(self):
        """Test parsing tool call using 'arguments' instead of 'args'."""
        message = create_mock_message(
            [
                {
                    "id": "call_123",
                    "name": "bash_execute",
                    "arguments": {"command": "date"},
                }
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].arguments == {"command": "date"}

    def test_parse_tool_call_with_json_string_args(self):
        """Test parsing tool call with JSON string arguments."""
        import json

        message = create_mock_message(
            [
                {
                    "id": "call_123",
                    "name": "bash_execute",
                    "args": json.dumps({"command": "ls -la", "timeout": 30}),
                }
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].arguments == {"command": "ls -la", "timeout": 30}

    def test_parse_empty_tool_calls_list(self):
        """Test parsing message with empty tool_calls list."""
        message = create_mock_message([])

        parsed = parse_tool_calls(message)

        assert len(parsed) == 0

    def test_parse_none_message(self):
        """Test parsing None message."""
        parsed = parse_tool_calls(None)  # type: ignore[arg-type]

        assert len(parsed) == 0

    def test_parse_message_without_tool_calls_attribute(self):
        """Test parsing message without tool_calls attribute."""
        message = create_mock_message(None)

        parsed = parse_tool_calls(message)

        assert len(parsed) == 0

    def test_parse_skips_tool_call_missing_id(self):
        """Test that tool call without ID is skipped."""
        message = create_mock_message(
            [
                {"name": "bash_execute", "args": {"command": "ls"}},  # Missing ID
                {
                    "id": "call_456",
                    "name": "bash_execute",
                    "args": {"command": "pwd"},
                },  # Valid
            ]
        )

        parsed = parse_tool_calls(message)

        # Should only parse the valid one
        assert len(parsed) == 1
        assert parsed[0].id == "call_456"

    def test_parse_skips_tool_call_missing_name(self):
        """Test that tool call without name is skipped."""
        message = create_mock_message(
            [
                {"id": "call_123", "args": {"command": "ls"}},  # Missing name
                {
                    "id": "call_456",
                    "name": "bash_execute",
                    "args": {"command": "pwd"},
                },  # Valid
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].name == "bash_execute"

    def test_parse_skips_tool_call_invalid_json_args(self):
        """Test that tool call with invalid JSON args is skipped."""
        message = create_mock_message(
            [
                {
                    "id": "call_123",
                    "name": "bash_execute",
                    "args": "{invalid json}",  # Invalid JSON
                },
                {
                    "id": "call_456",
                    "name": "bash_execute",
                    "args": {"command": "pwd"},
                },  # Valid
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].id == "call_456"

    def test_parse_skips_tool_call_non_dict_non_string_args(self):
        """Test that tool call with invalid args type is skipped."""
        message = create_mock_message(
            [
                {
                    "id": "call_123",
                    "name": "bash_execute",
                    "args": ["list", "args"],  # Invalid type
                },
                {
                    "id": "call_456",
                    "name": "bash_execute",
                    "args": {"command": "pwd"},
                },
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].id == "call_456"

    def test_parse_skips_non_dict_tool_call(self):
        """Test that non-dict tool call entries are skipped."""
        message = create_mock_message(
            [
                "invalid_tool_call",  # Not a dict
                {
                    "id": "call_456",
                    "name": "bash_execute",
                    "args": {"command": "pwd"},
                },
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].id == "call_456"

    def test_parse_handles_exception_gracefully(self):
        """Test that parser doesn't crash on unexpected errors."""
        # Create a tool call that will raise an exception during parsing
        problematic_call = {
            "id": "call_123",
            "name": "bash_execute",
            "args": {"command": "test"},
        }

        # Mock to raise exception when accessing 'id'
        class BrokenDict(dict):
            def get(self, key, default=None):
                if key == "id":
                    raise RuntimeError("Simulated error")
                return super().get(key, default)

        message = create_mock_message([BrokenDict(problematic_call)])

        # Should not raise, just return empty list
        parsed = parse_tool_calls(message)

        assert len(parsed) == 0

    def test_parse_preserves_raw_tool_call(self):
        """Test that original raw tool call is preserved."""
        original_call = {
            "id": "call_123",
            "name": "bash_execute",
            "args": {"command": "ls"},
            "extra_field": "preserved",
        }
        message = create_mock_message([original_call])

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].raw == original_call
        assert parsed[0].raw.get("extra_field") == "preserved"

    def test_parse_complex_arguments(self):
        """Test parsing tool call with complex nested arguments."""
        message = create_mock_message(
            [
                {
                    "id": "call_123",
                    "name": "complex_tool",
                    "args": {
                        "nested": {
                            "level1": {"level2": "value"},
                            "list": [1, 2, 3],
                        },
                        "boolean": True,
                        "number": 42,
                    },
                }
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].arguments["nested"]["level1"]["level2"] == "value"
        assert parsed[0].arguments["nested"]["list"] == [1, 2, 3]
        assert parsed[0].arguments["boolean"] is True
        assert parsed[0].arguments["number"] == 42


class TestHasToolCalls:
    """Tests for has_tool_calls helper function."""

    def test_has_tool_calls_with_tool_calls(self):
        """Test detecting message with tool calls."""
        message = create_mock_message(
            [{"id": "call_123", "name": "bash_execute", "args": {}}]
        )

        assert has_tool_calls(message) is True

    def test_has_tool_calls_with_empty_list(self):
        """Test detecting message with empty tool_calls list."""
        message = create_mock_message([])

        assert has_tool_calls(message) is False

    def test_has_tool_calls_without_attribute(self):
        """Test detecting message without tool_calls attribute."""
        message = create_mock_message(None)

        assert has_tool_calls(message) is False

    def test_has_tool_calls_with_none_message(self):
        """Test detecting None message."""
        assert has_tool_calls(None) is False

    def test_has_tool_calls_with_multiple_calls(self):
        """Test detecting message with multiple tool calls."""
        message = create_mock_message(
            [
                {"id": "call_1", "name": "tool1", "args": {}},
                {"id": "call_2", "name": "tool2", "args": {}},
            ]
        )

        assert has_tool_calls(message) is True


class TestParserIntegration:
    """Integration tests for parser with realistic scenarios."""

    def test_parse_bash_execute_tool_call(self):
        """Test parsing a realistic bash_execute tool call."""
        message = create_mock_message(
            [
                {
                    "id": "call_CjKxQfD8YRVNX9zP",
                    "name": "bash_execute",
                    "args": {
                        "command": "ls -la /tmp",
                        "timeout": 30,
                        "working_directory": "/home/user",
                    },
                }
            ]
        )

        parsed = parse_tool_calls(message)

        assert len(parsed) == 1
        assert parsed[0].name == "bash_execute"
        assert parsed[0].arguments["command"] == "ls -la /tmp"
        assert parsed[0].arguments["timeout"] == 30
        assert parsed[0].arguments["working_directory"] == "/home/user"

    def test_parse_mixed_valid_and_invalid_calls(self):
        """Test parsing a mix of valid and invalid tool calls."""
        message = create_mock_message(
            [
                {
                    "id": "call_1",
                    "name": "valid_tool",
                    "args": {"param": "value"},
                },  # Valid
                {"name": "missing_id", "args": {}},  # Invalid: no ID
                {
                    "id": "call_2",
                    "args": {"param": "value"},
                },  # Invalid: no name
                {
                    "id": "call_3",
                    "name": "invalid_json",
                    "args": "{bad json",
                },  # Invalid: bad JSON
                {
                    "id": "call_4",
                    "name": "another_valid",
                    "args": {"x": 1},
                },  # Valid
            ]
        )

        parsed = parse_tool_calls(message)

        # Should only get the 2 valid ones
        assert len(parsed) == 2
        assert parsed[0].name == "valid_tool"
        assert parsed[1].name == "another_valid"

    def test_workflow_check_then_parse(self):
        """Test typical workflow: check for calls, then parse."""
        message = create_mock_message(
            [{"id": "call_123", "name": "bash_execute", "args": {"command": "pwd"}}]
        )

        # Typical usage pattern
        if has_tool_calls(message):
            parsed = parse_tool_calls(message)
            assert len(parsed) == 1
            assert parsed[0].name == "bash_execute"
        else:
            pytest.fail("Should have detected tool calls")
