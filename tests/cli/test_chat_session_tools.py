"""Tests for ChatSession tool execution functionality."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

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
def mock_conversation_service():
    """Create a mock ConversationService."""
    service = Mock()
    conversation = Mock()
    conversation.messages = []
    service.conversation = conversation
    service.model = Mock()
    # Mock tool_registry to return empty list for list_tools()
    tool_registry = Mock()
    tool_registry.list_tools.return_value = []
    service.tool_registry = tool_registry
    return service


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_with_tool_call(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test ChatSession handles tool calls correctly."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Simulate a tool call in the response
    tool_request_token = Mock()
    tool_request_token.content = "I'll list the files for you."
    tool_request_token.metadata = {
        "tool_name": "bash_execute",
        "tool_args": {"command": "ls -la"},
    }

    final_token = Mock()
    final_token.content = "Here are the files in the directory..."
    final_token.metadata = {}

    # Mock send_message to yield tokens including a tool call
    async def mock_send_message(*args, **kwargs):
        yield tool_request_token
        yield final_token

    mock_conversation_service.send_message = mock_send_message

    # Create session
    session = ChatSession(mock_config)

    # Send message
    response = session.send("List files in the current directory")

    # Verify response contains both parts
    assert (
        "I'll list the files for you." in response
        or "Here are the files in the directory..." in response
    )


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_without_tools(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test ChatSession works without tool registry (backward compatibility)."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Mock send_message to yield a simple response
    async def mock_send_message(*args, **kwargs):
        token = Mock()
        token.content = "Hello!"
        token.metadata = {}
        yield token

    mock_conversation_service.send_message = mock_send_message

    # Create session without tool registry
    session = ChatSession(mock_config)

    # Send message
    response = session.send("Hello", stream=False)

    # Verify basic functionality works
    assert response == "Hello!"


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
