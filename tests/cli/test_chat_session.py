"""Tests for ChatSession class."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

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
def mock_chat_model():
    """Create a mock chat model."""
    model = Mock()

    # Mock invoke to return AIMessage
    response = AIMessage(content="Hello! How can I help you?")
    model.invoke = Mock(return_value=response)

    # Mock stream to return chunks
    def mock_stream(messages):
        chunks = ["Hello", "! ", "How ", "can ", "I ", "help ", "you", "?"]
        for chunk in chunks:
            mock_chunk = Mock()
            mock_chunk.content = chunk
            mock_chunk.tool_call_chunks = []  # No tool calls
            yield mock_chunk

    model.stream = Mock(side_effect=mock_stream)

    return model


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_chat_session_initialization(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test ChatSession initializes correctly."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history_class.return_value = mock_history

    session = ChatSession(mock_config)

    assert session.config == mock_config
    assert session.model == mock_chat_model
    assert session.history == mock_history

    # Verify get_chat_model was called correctly
    mock_get_chat_model.assert_called_once()

    # Verify ConversationHistory was initialized
    mock_history_class.assert_called_once()

    # Verify system prompt was added
    mock_history.add_system_message.assert_called_once_with(
        "You are a helpful assistant."
    )


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_chat_session_send_non_streaming(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test sending a message without streaming."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.get_messages = Mock(return_value=[HumanMessage(content="Hello")])
    mock_history_class.return_value = mock_history

    session = ChatSession(mock_config)
    response = session.send("Hello", stream=False)

    assert response == "Hello! How can I help you?"

    # Verify message was added to history
    mock_history.add_user_message.assert_called_once_with("Hello")
    mock_history.add_assistant_message.assert_called_once_with(
        "Hello! How can I help you?"
    )


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
@patch("consoul.cli.chat_session.stream_response")
def test_chat_session_send_streaming(
    mock_stream_response,
    mock_history_class,
    mock_get_chat_model,
    mock_config,
    mock_chat_model,
):
    """Test sending a message with streaming."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.get_messages = Mock(return_value=[HumanMessage(content="Hello")])
    mock_history_class.return_value = mock_history

    # Mock stream_response to return complete text
    mock_stream_response.return_value = "Hello! How can I help you?"

    session = ChatSession(mock_config)
    response = session.send("Hello", stream=True)

    assert response == "Hello! How can I help you?"

    # Verify stream_response was called
    mock_stream_response.assert_called_once()

    # Verify messages were added to history
    mock_history.add_user_message.assert_called_once_with("Hello")
    mock_history.add_assistant_message.assert_called_once_with(
        "Hello! How can I help you?"
    )


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_chat_session_clear_history(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test clearing conversation history."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()

    # Mock messages with system and user messages
    system_msg = Mock()
    system_msg.type = "system"
    user_msg = Mock()
    user_msg.type = "human"

    mock_history.messages = [system_msg, user_msg]
    mock_history_class.return_value = mock_history

    session = ChatSession(mock_config)
    session.clear_history()

    # Verify only system message remains
    assert len(mock_history.messages) == 1
    assert mock_history.messages[0] == system_msg


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_chat_session_get_stats(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test getting conversation statistics."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.__len__ = Mock(return_value=5)
    mock_history.count_tokens = Mock(return_value=150)
    mock_history_class.return_value = mock_history

    session = ChatSession(mock_config)
    stats = session.get_stats()

    assert stats == {"message_count": 5, "token_count": 150}


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_chat_session_context_manager(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test ChatSession as context manager."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.session_id = "test-session-123"
    mock_history_class.return_value = mock_history

    with ChatSession(mock_config) as session:
        assert session is not None
        assert session.model == mock_chat_model

    # Context manager should exit cleanly


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
@patch("consoul.cli.chat_session.Markdown")
def test_chat_session_markdown_rendering_non_streaming(
    mock_markdown_class,
    mock_history_class,
    mock_get_chat_model,
    mock_config,
    mock_chat_model,
):
    """Test markdown rendering for non-streaming responses."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.get_messages = Mock(
        return_value=[HumanMessage(content="Show me code")]
    )
    mock_history_class.return_value = mock_history

    # Mock response with markdown
    response_text = "Here's some code:\n```python\nprint('Hello')\n```"
    mock_chat_model.invoke.return_value = AIMessage(content=response_text)

    # Mock Markdown instance
    mock_md = Mock()
    mock_markdown_class.return_value = mock_md

    session = ChatSession(mock_config)

    # Mock the console.print to verify it was called
    with patch.object(session.console, "print") as mock_print:
        response = session.send("Show me code", stream=False, render_markdown=True)

    assert response == response_text

    # Verify Markdown was created with response text
    mock_markdown_class.assert_called_once_with(response_text)

    # Verify markdown object was printed
    assert any(
        call[0][0] == mock_md for call in mock_print.call_args_list if call[0]
    ), "Markdown object should be printed"


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_chat_session_plain_text_non_streaming(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test plain text rendering when markdown is disabled."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.get_messages = Mock(return_value=[HumanMessage(content="Hello")])
    mock_history_class.return_value = mock_history

    session = ChatSession(mock_config)
    response = session.send("Hello", stream=False, render_markdown=False)

    assert response == "Hello! How can I help you?"

    # Verify plain text was printed (not Markdown)
    assert mock_history.add_assistant_message.called


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
@patch("consoul.cli.chat_session.stream_response")
def test_chat_session_markdown_rendering_streaming(
    mock_stream_response,
    mock_history_class,
    mock_get_chat_model,
    mock_config,
    mock_chat_model,
):
    """Test markdown rendering is passed to stream_response."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.get_messages = Mock(
        return_value=[HumanMessage(content="Show me code")]
    )
    mock_history_class.return_value = mock_history

    # Mock stream_response to return markdown content
    response_text = "```python\nprint('test')\n```"
    mock_stream_response.return_value = response_text

    session = ChatSession(mock_config)
    response = session.send("Show me code", stream=True, render_markdown=True)

    assert response == response_text

    # Verify stream_response was called with render_markdown=True
    call_kwargs = mock_stream_response.call_args[1]
    assert call_kwargs["render_markdown"] is True


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
@patch("consoul.cli.chat_session.stream_response")
def test_chat_session_plain_text_streaming(
    mock_stream_response,
    mock_history_class,
    mock_get_chat_model,
    mock_config,
    mock_chat_model,
):
    """Test plain text streaming when markdown is disabled."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.get_messages = Mock(return_value=[HumanMessage(content="Hello")])
    mock_history_class.return_value = mock_history

    mock_stream_response.return_value = "Hello! How can I help you?"

    session = ChatSession(mock_config)
    response = session.send("Hello", stream=True, render_markdown=False)

    assert response == "Hello! How can I help you?"

    # Verify stream_response was called with render_markdown=False
    call_kwargs = mock_stream_response.call_args[1]
    assert call_kwargs["render_markdown"] is False


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
@patch("consoul.cli.chat_session.stream_response")
def test_chat_session_streaming_error_handling(
    mock_stream_response,
    mock_history_class,
    mock_get_chat_model,
    mock_config,
    mock_chat_model,
):
    """Test that StreamingError is properly caught and handled."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.get_messages = Mock(return_value=[HumanMessage(content="Hello")])
    mock_history_class.return_value = mock_history

    # Mock stream_response to raise StreamingError with partial response
    partial_text = "Hello! How can I"
    mock_stream_response.side_effect = StreamingError(
        "Streaming interrupted by user", partial_response=partial_text
    )

    session = ChatSession(mock_config)

    # Should raise KeyboardInterrupt (not StreamingError)
    with pytest.raises(KeyboardInterrupt):
        session.send("Hello", stream=True)

    # Verify _interrupted flag was set
    assert session._interrupted is True

    # Verify partial response was saved to history
    mock_history.add_assistant_message.assert_called_once_with(partial_text)


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
@patch("consoul.cli.chat_session.stream_response")
def test_chat_session_streaming_error_no_partial(
    mock_stream_response,
    mock_history_class,
    mock_get_chat_model,
    mock_config,
    mock_chat_model,
):
    """Test StreamingError without partial response."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history.get_messages = Mock(return_value=[HumanMessage(content="Hello")])
    mock_history_class.return_value = mock_history

    # Mock stream_response to raise StreamingError with no partial response
    mock_stream_response.side_effect = StreamingError(
        "Streaming interrupted by user", partial_response=""
    )

    session = ChatSession(mock_config)

    # Should raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        session.send("Hello", stream=True)

    # Verify _interrupted flag was set
    assert session._interrupted is True

    # Verify no partial response was saved (empty string)
    mock_history.add_assistant_message.assert_not_called()
