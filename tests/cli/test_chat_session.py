"""Tests for ChatSession class."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from consoul.ai.exceptions import StreamingError
from consoul.cli import ChatSession


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

    # Mock profile with system prompt
    profile = Mock()
    profile.system_prompt = "You are a helpful assistant."
    config.get_active_profile = Mock(return_value=profile)

    return config


@pytest.fixture
def mock_conversation_service():
    """Create a mock ConversationService."""
    service = Mock()
    conversation = Mock()
    conversation.messages = []
    conversation.count_tokens = Mock(return_value=150)
    conversation.session_id = "test-session-123"
    service.conversation = conversation
    service.model = Mock()
    # Mock tool_registry to return empty list for list_tools()
    tool_registry = Mock()
    tool_registry.list_tools.return_value = []
    service.tool_registry = tool_registry
    return service


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_initialization(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test ChatSession initializes correctly."""
    mock_service_class.from_config.return_value = mock_conversation_service

    session = ChatSession(mock_config)

    assert session.config == mock_config
    assert session.conversation_service == mock_conversation_service

    # Verify from_config was called
    mock_service_class.from_config.assert_called_once()


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_send_non_streaming(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test sending a message without streaming."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Mock send_message to yield tokens
    async def mock_send_message(*args, **kwargs):
        token = Mock()
        token.content = "Hello! How can I help you?"
        token.metadata = {}
        yield token

    mock_conversation_service.send_message = mock_send_message

    session = ChatSession(mock_config)
    response = session.send("Hello", stream=False)

    assert response == "Hello! How can I help you?"


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_send_streaming(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test sending a message with streaming."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Mock send_message to yield tokens
    async def mock_send_message(*args, **kwargs):
        for chunk in ["Hello", "! ", "How can I help you?"]:
            token = Mock()
            token.content = chunk
            token.metadata = {}
            yield token

    mock_conversation_service.send_message = mock_send_message

    session = ChatSession(mock_config)
    response = session.send("Hello", stream=True)

    assert response == "Hello! How can I help you?"


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_clear_history(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test clearing conversation history."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Mock messages with system and user messages
    system_msg = Mock()
    system_msg.type = "system"
    user_msg = Mock()
    user_msg.type = "human"

    mock_conversation_service.conversation.messages = [system_msg, user_msg]

    session = ChatSession(mock_config)
    session.clear_history()

    # Verify only system message remains
    assert len(mock_conversation_service.conversation.messages) == 1
    assert mock_conversation_service.conversation.messages[0] == system_msg


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_get_stats(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test getting conversation statistics."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Create mock messages (2 system, 3 user, 2 assistant = 5 user+assistant)
    system_msg1 = Mock()
    system_msg1.type = "system"
    system_msg2 = Mock()
    system_msg2.type = "system"
    user_msg1 = Mock()
    user_msg1.type = "human"
    ai_msg1 = Mock()
    ai_msg1.type = "ai"
    user_msg2 = Mock()
    user_msg2.type = "human"
    ai_msg2 = Mock()
    ai_msg2.type = "ai"
    user_msg3 = Mock()
    user_msg3.type = "human"

    mock_conversation_service.conversation.messages = [
        system_msg1,
        system_msg2,
        user_msg1,
        ai_msg1,
        user_msg2,
        ai_msg2,
        user_msg3,
    ]

    session = ChatSession(mock_config)
    stats = session.get_stats()

    # Should count only human and ai messages (5 total), not system messages (2)
    assert stats == {"message_count": 5, "token_count": 150}


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_context_manager(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test ChatSession as context manager."""
    mock_service_class.from_config.return_value = mock_conversation_service

    with ChatSession(mock_config) as session:
        assert session is not None
        assert session.conversation_service == mock_conversation_service

    # Context manager should exit cleanly


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_markdown_rendering_non_streaming(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test markdown rendering for non-streaming responses."""
    mock_service_class.from_config.return_value = mock_conversation_service

    response_text = "Here's some code:\n```python\nprint('Hello')\n```"

    # Mock send_message to yield the response
    async def mock_send_message(*args, **kwargs):
        token = Mock()
        token.content = response_text
        token.metadata = {}
        yield token

    mock_conversation_service.send_message = mock_send_message

    session = ChatSession(mock_config)
    response = session.send("Show me code", stream=False, render_markdown=True)

    assert response == response_text


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_plain_text_non_streaming(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test plain text rendering when markdown is disabled."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Mock send_message to yield the response
    async def mock_send_message(*args, **kwargs):
        token = Mock()
        token.content = "Hello! How can I help you?"
        token.metadata = {}
        yield token

    mock_conversation_service.send_message = mock_send_message

    session = ChatSession(mock_config)
    response = session.send("Hello", stream=False, render_markdown=False)

    assert response == "Hello! How can I help you?"


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_markdown_rendering_streaming(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test markdown rendering is handled during streaming."""
    mock_service_class.from_config.return_value = mock_conversation_service

    response_text = "```python\nprint('test')\n```"

    # Mock send_message to yield the response
    async def mock_send_message(*args, **kwargs):
        token = Mock()
        token.content = response_text
        token.metadata = {}
        yield token

    mock_conversation_service.send_message = mock_send_message

    session = ChatSession(mock_config)
    response = session.send("Show me code", stream=True, render_markdown=True)

    assert response == response_text


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_plain_text_streaming(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test plain text streaming when markdown is disabled."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Mock send_message to yield the response
    async def mock_send_message(*args, **kwargs):
        token = Mock()
        token.content = "Hello! How can I help you?"
        token.metadata = {}
        yield token

    mock_conversation_service.send_message = mock_send_message

    session = ChatSession(mock_config)
    response = session.send("Hello", stream=True, render_markdown=False)

    assert response == "Hello! How can I help you?"


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_streaming_error_handling(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test that StreamingError is properly caught and handled."""
    mock_service_class.from_config.return_value = mock_conversation_service

    partial_text = "Hello! How can I"

    # Mock send_message to raise StreamingError
    async def mock_send_message(*args, **kwargs):
        raise StreamingError(
            "Streaming interrupted by user", partial_response=partial_text
        )
        yield  # Make it a generator

    mock_conversation_service.send_message = mock_send_message

    session = ChatSession(mock_config)

    # Should raise KeyboardInterrupt (not StreamingError)
    with pytest.raises(KeyboardInterrupt):
        session.send("Hello", stream=True)

    # Verify _interrupted flag was set
    assert session._interrupted is True


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_streaming_error_no_partial(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test StreamingError without partial response."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Mock send_message to raise StreamingError with no partial response
    async def mock_send_message(*args, **kwargs):
        raise StreamingError("Streaming interrupted by user", partial_response="")
        yield  # Make it a generator

    mock_conversation_service.send_message = mock_send_message

    session = ChatSession(mock_config)

    # Should raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        session.send("Hello", stream=True)

    # Verify _interrupted flag was set
    assert session._interrupted is True


# =============================================================================
# Test: Session Resumption (SOUL-355)
# =============================================================================


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_passes_resume_session_id_to_from_config(
    mock_service_class, mock_config
):
    """Test ChatSession passes resume_session_id to ConversationService.from_config()."""
    mock_service = Mock()
    mock_service.conversation = Mock()
    mock_service.conversation.messages = []
    mock_service_class.from_config.return_value = mock_service

    ChatSession(mock_config, resume_session_id="abc-123")

    # Verify from_config was called with session_id
    mock_service_class.from_config.assert_called_once()
    call_kwargs = mock_service_class.from_config.call_args[1]
    assert call_kwargs["session_id"] == "abc-123"


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_resume_does_not_add_system_prompt(
    mock_service_class, mock_config
):
    """Test that system prompt is NOT added when resuming a session."""
    mock_service = Mock()
    mock_conversation = Mock()
    mock_conversation.messages = []
    mock_service.conversation = mock_conversation
    mock_service_class.from_config.return_value = mock_service

    ChatSession(mock_config, resume_session_id="existing-session")

    # Verify add_system_message was NOT called (system prompt is in the loaded history)
    mock_conversation.add_system_message.assert_not_called()


@patch("consoul.cli.chat_session.ConversationService")
def test_chat_session_without_resume_adds_system_prompt(
    mock_service_class, mock_config
):
    """Test that system prompt IS added when NOT resuming a session."""
    mock_service = Mock()
    mock_conversation = Mock()
    mock_conversation.messages = []
    mock_service.conversation = mock_conversation
    # Mock tool_registry to return empty list for list_tools()
    mock_tool_registry = Mock()
    mock_tool_registry.list_tools.return_value = []
    mock_service.tool_registry = mock_tool_registry
    mock_service_class.from_config.return_value = mock_service

    ChatSession(mock_config)

    # Verify add_system_message WAS called (new session gets system prompt)
    mock_conversation.add_system_message.assert_called_once()
