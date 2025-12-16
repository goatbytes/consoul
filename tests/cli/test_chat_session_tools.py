"""Tests for ChatSession tool execution functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from consoul.cli import ChatSession, CliToolApprovalProvider


@pytest.fixture
def mock_config():
    """Create a mock ConsoulConfig for testing."""
    config = Mock()
    config.current_provider = Mock(value="openai")
    config.current_model = "gpt-4o-mini"
    config.persist = False

    # Mock model config
    model_config = Mock()
    model_config.model = "gpt-4o-mini"
    model_config.provider = "openai"
    config.get_current_model_config = Mock(return_value=model_config)

    # Mock profile
    profile = Mock()
    profile.system_prompt = None
    profile.conversation = Mock(persist=False)
    config.get_active_profile = Mock(return_value=profile)

    return config


@pytest.fixture
def mock_tool_registry():
    """Create a mock ToolRegistry."""
    registry = Mock()
    registry.__len__ = Mock(return_value=1)

    # Mock bind_to_model
    def bind_to_model(model):
        return model

    registry.bind_to_model = Mock(side_effect=bind_to_model)

    # Mock request_tool_approval
    async def mock_request_approval(tool_name, arguments, tool_call_id):
        response = Mock()
        response.approved = True
        return response

    registry.request_tool_approval = AsyncMock(side_effect=mock_request_approval)

    # Mock get_tool
    tool_metadata = Mock()
    tool_metadata.tool = Mock()
    tool_metadata.tool.invoke = Mock(return_value="Command output: files listed")
    registry.get_tool = Mock(return_value=tool_metadata)

    return registry


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
@patch("consoul.cli.chat_session.stream_response")
def test_chat_session_with_tool_call(
    mock_stream_response,
    mock_history_class,
    mock_get_chat_model,
    mock_config,
    mock_tool_registry,
):
    """Test ChatSession handles tool calls correctly."""
    # Setup mocks
    mock_model = Mock()
    mock_get_chat_model.return_value = mock_model

    mock_history = Mock()
    mock_history.messages = []
    mock_history.get_messages = Mock(return_value=[])
    mock_history.add_user_message = Mock()
    mock_history.add_assistant_message = Mock()
    mock_history_class.return_value = mock_history

    # First response: AI requests tool execution
    ai_message_with_tool = AIMessage(
        content="I'll list the files for you.",
        tool_calls=[
            {
                "name": "bash_execute",
                "args": {"command": "ls -la"},
                "id": "call_123",
                "type": "tool_call",
            }
        ],
    )

    # Second response: AI responds after tool execution
    ai_message_final = AIMessage(
        content="Here are the files in the directory...", tool_calls=[]
    )

    # Mock stream_response to return different responses
    mock_stream_response.side_effect = [
        ("I'll list the files for you.", ai_message_with_tool),
        ("Here are the files in the directory...", ai_message_final),
    ]

    # Create session with tool registry
    approval_provider = CliToolApprovalProvider()
    session = ChatSession(
        mock_config,
        tool_registry=mock_tool_registry,
        approval_provider=approval_provider,
    )

    # Send message
    session.send("List files in the current directory")

    # Verify tool execution workflow
    assert mock_stream_response.call_count == 2  # Two iterations (tool request + final)
    assert mock_tool_registry.request_tool_approval.call_count == 1

    # Verify approval was requested
    approval_call = mock_tool_registry.request_tool_approval.call_args
    assert approval_call[1]["tool_name"] == "bash_execute"
    assert approval_call[1]["arguments"] == {"command": "ls -la"}

    # Verify tool was executed
    assert mock_tool_registry.get_tool.call_count == 1
    assert mock_tool_registry.get_tool.call_args[0][0] == "bash_execute"

    # Verify ToolMessage was added to history
    tool_messages = [
        msg for msg in mock_history.messages if isinstance(msg, ToolMessage)
    ]
    assert len(tool_messages) == 1
    assert "Command output" in tool_messages[0].content


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_chat_session_without_tools(
    mock_history_class, mock_get_chat_model, mock_config
):
    """Test ChatSession works without tool registry (backward compatibility)."""
    # Setup mocks
    mock_model = Mock()
    mock_get_chat_model.return_value = mock_model

    mock_history = Mock()
    mock_history.messages = []
    mock_history.get_messages = Mock(return_value=[])
    mock_history.add_user_message = Mock()
    mock_history.add_assistant_message = Mock()
    mock_history_class.return_value = mock_history

    # Mock invoke (non-streaming)
    mock_model.invoke = Mock(return_value=AIMessage(content="Hello!"))

    # Create session without tool registry
    session = ChatSession(mock_config)

    # Send message
    response = session.send("Hello", stream=False)

    # Verify basic functionality works
    assert response == "Hello!"
    assert mock_history.add_user_message.call_count == 1
    assert mock_history.add_assistant_message.call_count == 1


def test_cli_approval_provider_always_approve():
    """Test CliToolApprovalProvider tracks always_approve decisions."""

    provider = CliToolApprovalProvider()

    # Simulate user choosing "always approve"
    provider.always_approve.add("bash_execute")

    # Check if tool is in always_approve set
    assert "bash_execute" in provider.always_approve
    assert "grep_search" not in provider.always_approve


def test_cli_approval_provider_never_approve():
    """Test CliToolApprovalProvider tracks never_approve decisions."""
    provider = CliToolApprovalProvider()

    # Simulate user choosing "never approve"
    provider.never_approve.add("dangerous_tool")

    # Check if tool is in never_approve set
    assert "dangerous_tool" in provider.never_approve
    assert "bash_execute" not in provider.never_approve


def test_cli_approval_provider_clear_session_state():
    """Test clearing session approval state."""
    provider = CliToolApprovalProvider()

    # Add some approvals
    provider.always_approve.add("bash_execute")
    provider.never_approve.add("dangerous_tool")

    # Clear state
    provider.clear_session_state()

    # Verify sets are empty
    assert len(provider.always_approve) == 0
    assert len(provider.never_approve) == 0
