"""Tests for conversation history management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from consoul.ai.history import (
    ConversationHistory,
    to_dict_message,
    to_langchain_message,
)


class TestMessageConversion:
    """Tests for message format conversion utilities."""

    def test_to_langchain_message_system(self):
        """Test converting system role to SystemMessage."""
        msg = to_langchain_message("system", "You are helpful")
        assert isinstance(msg, SystemMessage)
        assert msg.content == "You are helpful"

    def test_to_langchain_message_user(self):
        """Test converting user role to HumanMessage."""
        msg = to_langchain_message("user", "Hello")
        assert isinstance(msg, HumanMessage)
        assert msg.content == "Hello"

        # Test "human" alias
        msg2 = to_langchain_message("human", "Hi")
        assert isinstance(msg2, HumanMessage)

    def test_to_langchain_message_assistant(self):
        """Test converting assistant role to AIMessage."""
        msg = to_langchain_message("assistant", "Hello there")
        assert isinstance(msg, AIMessage)
        assert msg.content == "Hello there"

        # Test "ai" alias
        msg2 = to_langchain_message("ai", "Hi there")
        assert isinstance(msg2, AIMessage)

    def test_to_langchain_message_case_insensitive(self):
        """Test role names are case-insensitive."""
        msg1 = to_langchain_message("USER", "test")
        msg2 = to_langchain_message("User", "test")
        msg3 = to_langchain_message("user", "test")

        assert isinstance(msg1, HumanMessage)
        assert isinstance(msg2, HumanMessage)
        assert isinstance(msg3, HumanMessage)

    def test_to_langchain_message_invalid_role(self):
        """Test error on invalid role."""
        with pytest.raises(ValueError, match="Unknown message role"):
            to_langchain_message("invalid", "test")

    def test_to_dict_message_system(self):
        """Test converting SystemMessage to dict."""
        msg = SystemMessage(content="You are helpful")
        result = to_dict_message(msg)
        assert result == {"role": "system", "content": "You are helpful"}

    def test_to_dict_message_human(self):
        """Test converting HumanMessage to dict."""
        msg = HumanMessage(content="Hello")
        result = to_dict_message(msg)
        assert result == {"role": "user", "content": "Hello"}

    def test_to_dict_message_ai(self):
        """Test converting AIMessage to dict."""
        msg = AIMessage(content="Hi there")
        result = to_dict_message(msg)
        assert result == {"role": "assistant", "content": "Hi there"}


class TestConversationHistoryBasics:
    """Tests for basic ConversationHistory functionality."""

    def test_initialization_default_token_limit(self):
        """Test history initializes with model's default token limit."""
        history = ConversationHistory("gpt-4o")

        assert history.model_name == "gpt-4o"
        assert history.max_tokens == 128_000  # gpt-4o's limit
        assert len(history.messages) == 0

    def test_initialization_custom_token_limit(self):
        """Test history with custom token limit override."""
        history = ConversationHistory("gpt-4o", max_tokens=4000)

        assert history.max_tokens == 4000

    def test_add_system_message(self):
        """Test adding system message."""
        history = ConversationHistory("gpt-4o")
        history.add_system_message("You are helpful")

        assert len(history) == 1
        assert isinstance(history.messages[0], SystemMessage)
        assert history.messages[0].content == "You are helpful"

    def test_add_system_message_replaces_existing(self):
        """Test that adding system message replaces previous one."""
        history = ConversationHistory("gpt-4o")
        history.add_system_message("First")
        history.add_system_message("Second")

        # Should only have one system message
        assert len(history) == 1
        assert history.messages[0].content == "Second"

    def test_add_user_message(self):
        """Test adding user message."""
        history = ConversationHistory("gpt-4o")
        history.add_user_message("Hello!")

        assert len(history) == 1
        assert isinstance(history.messages[0], HumanMessage)
        assert history.messages[0].content == "Hello!"

    def test_add_assistant_message(self):
        """Test adding assistant message."""
        history = ConversationHistory("gpt-4o")
        history.add_assistant_message("Hi there!")

        assert len(history) == 1
        assert isinstance(history.messages[0], AIMessage)
        assert history.messages[0].content == "Hi there!"

    def test_add_message_generic(self):
        """Test generic add_message method with different roles."""
        history = ConversationHistory("gpt-4o")

        history.add_message("system", "System message")
        history.add_message("user", "User message")
        history.add_message("assistant", "Assistant message")

        assert len(history) == 3
        assert isinstance(history.messages[0], SystemMessage)
        assert isinstance(history.messages[1], HumanMessage)
        assert isinstance(history.messages[2], AIMessage)

    def test_add_message_invalid_role(self):
        """Test error when adding message with invalid role."""
        history = ConversationHistory("gpt-4o")

        with pytest.raises(ValueError, match="Unknown role"):
            history.add_message("invalid", "test")


class TestConversationHistoryRetrieval:
    """Tests for retrieving messages from history."""

    def test_get_messages_returns_copy(self):
        """Test get_messages returns a copy, not reference."""
        history = ConversationHistory("gpt-4o")
        history.add_user_message("Hello")

        messages1 = history.get_messages()
        messages2 = history.get_messages()

        # Should be equal but not same object
        assert messages1 == messages2
        assert messages1 is not messages2

    def test_get_messages_as_dicts(self):
        """Test converting messages to dict format."""
        history = ConversationHistory("gpt-4o")
        history.add_system_message("System")
        history.add_user_message("User")
        history.add_assistant_message("Assistant")

        dicts = history.get_messages_as_dicts()

        assert len(dicts) == 3
        assert dicts[0] == {"role": "system", "content": "System"}
        assert dicts[1] == {"role": "user", "content": "User"}
        assert dicts[2] == {"role": "assistant", "content": "Assistant"}

    def test_get_messages_preserves_order(self):
        """Test that message order is preserved."""
        history = ConversationHistory("gpt-4o")

        for i in range(5):
            history.add_user_message(f"Message {i}")

        messages = history.get_messages()

        for i, msg in enumerate(messages):
            assert msg.content == f"Message {i}"


class TestConversationHistoryTokenCounting:
    """Tests for token counting in conversation history."""

    def test_count_tokens_uses_counter(self):
        """Test that count_tokens uses the token counter."""
        with patch("consoul.ai.context.create_token_counter") as mock_create_counter:
            mock_counter = MagicMock(return_value=42)
            mock_create_counter.return_value = mock_counter

            history = ConversationHistory("gpt-4o")
            history.add_user_message("Hello")

            tokens = history.count_tokens()

            assert tokens == 42
            mock_counter.assert_called_once()

    def test_count_tokens_empty_history(self):
        """Test counting tokens in empty history."""
        history = ConversationHistory("gpt-4o")

        tokens = history.count_tokens()

        assert tokens == 0

    def test_count_tokens_multiple_messages(self):
        """Test counting tokens with multiple messages."""

        # Mock counter that returns 10 tokens per message
        def mock_counter(messages):
            return len(messages) * 10

        with patch("consoul.ai.context.create_token_counter") as mock_create_counter:
            mock_create_counter.return_value = mock_counter

            history = ConversationHistory("gpt-4o")
            history.add_user_message("Message 1")
            history.add_assistant_message("Message 2")
            history.add_user_message("Message 3")

            tokens = history.count_tokens()

            assert tokens == 30  # 3 messages x 10 tokens


class TestConversationHistoryTrimming:
    """Tests for message trimming functionality."""

    @patch("consoul.ai.history.trim_messages")
    @patch("consoul.ai.history.create_token_counter")
    def test_get_trimmed_messages_calls_trim(
        self, mock_create_counter, mock_trim_messages
    ):
        """Test that get_trimmed_messages calls LangChain's trim_messages."""
        mock_counter = MagicMock(return_value=100)
        mock_create_counter.return_value = mock_counter

        mock_trimmed = [HumanMessage(content="trimmed")]
        mock_trim_messages.return_value = mock_trimmed

        history = ConversationHistory("gpt-4o", max_tokens=1000)
        history.add_system_message("System")
        history.add_user_message("User")

        result = history.get_trimmed_messages(reserve_tokens=200)

        # Verify trim_messages was called with correct params
        mock_trim_messages.assert_called_once()
        call_args = mock_trim_messages.call_args

        # Check positional args
        assert call_args[0][0] == history.messages

        # Check keyword args
        assert call_args[1]["max_tokens"] == 800  # 1000 - 200
        assert call_args[1]["strategy"] == "last"
        assert call_args[1]["include_system"] is True
        assert call_args[1]["start_on"] == "human"
        assert call_args[1]["allow_partial"] is False

        assert result == mock_trimmed

    @patch("consoul.ai.history.trim_messages")
    @patch("consoul.ai.history.create_token_counter")
    def test_get_trimmed_messages_fallback_on_error(
        self, mock_create_counter, mock_trim_messages
    ):
        """Test fallback to all messages if trimming fails."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        # Simulate trim_messages failing
        mock_trim_messages.side_effect = Exception("Trimming error")

        history = ConversationHistory("gpt-4o")
        history.add_user_message("Message")

        result = history.get_trimmed_messages()

        # Should return all messages as fallback
        assert len(result) == 1
        assert result[0].content == "Message"

    def test_get_trimmed_messages_empty_history(self):
        """Test trimming empty history returns empty list."""
        history = ConversationHistory("gpt-4o")

        result = history.get_trimmed_messages()

        assert result == []

    @patch("consoul.ai.history.trim_messages")
    @patch("consoul.ai.history.create_token_counter")
    def test_get_trimmed_messages_custom_strategy(
        self, mock_create_counter, mock_trim_messages
    ):
        """Test trimming with custom strategy."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter
        mock_trim_messages.return_value = []

        history = ConversationHistory("gpt-4o")
        history.add_user_message("Test")

        history.get_trimmed_messages(reserve_tokens=500, strategy="first")

        # Verify custom strategy was used
        call_args = mock_trim_messages.call_args
        assert call_args[1]["strategy"] == "first"
        assert call_args[1]["max_tokens"] == 128_000 - 500


class TestConversationHistoryClear:
    """Tests for clearing conversation history."""

    def test_clear_preserves_system_message_by_default(self):
        """Test that clear() preserves system message by default."""
        history = ConversationHistory("gpt-4o")
        history.add_system_message("System")
        history.add_user_message("User 1")
        history.add_assistant_message("Assistant 1")
        history.add_user_message("User 2")

        history.clear()

        assert len(history) == 1
        assert isinstance(history.messages[0], SystemMessage)
        assert history.messages[0].content == "System"

    def test_clear_without_preserving_system(self):
        """Test clearing all messages including system."""
        history = ConversationHistory("gpt-4o")
        history.add_system_message("System")
        history.add_user_message("User")

        history.clear(preserve_system=False)

        assert len(history) == 0

    def test_clear_no_system_message(self):
        """Test clearing when there's no system message."""
        history = ConversationHistory("gpt-4o")
        history.add_user_message("User")
        history.add_assistant_message("Assistant")

        history.clear(preserve_system=True)

        # Should clear all since there's no system message
        assert len(history) == 0

    def test_clear_empty_history(self):
        """Test clearing already empty history."""
        history = ConversationHistory("gpt-4o")

        history.clear()

        assert len(history) == 0


class TestConversationHistoryMagicMethods:
    """Tests for magic methods like __len__ and __repr__."""

    def test_len_returns_message_count(self):
        """Test __len__ returns number of messages."""
        history = ConversationHistory("gpt-4o")

        assert len(history) == 0

        history.add_user_message("Message 1")
        assert len(history) == 1

        history.add_assistant_message("Message 2")
        assert len(history) == 2

    def test_repr_shows_stats(self):
        """Test __repr__ shows model, message count, and tokens."""
        with patch("consoul.ai.context.create_token_counter") as mock_create_counter:
            mock_counter = MagicMock(return_value=100)
            mock_create_counter.return_value = mock_counter

            history = ConversationHistory("gpt-4o")
            history.add_user_message("Test")

            repr_str = repr(history)

            assert "gpt-4o" in repr_str
            assert "messages=1" in repr_str
            assert "tokens=100" in repr_str
            assert "128000" in repr_str  # max_tokens


class TestConversationHistoryWithModel:
    """Tests for ConversationHistory with LangChain model instance."""

    def test_initialization_with_model(self):
        """Test initializing history with model instance."""
        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 50

        history = ConversationHistory("claude-3-5-sonnet", model=mock_model)
        history.add_user_message("Test")

        tokens = history.count_tokens()

        # Should use model's token counter
        assert tokens == 50
        mock_model.get_num_tokens_from_messages.assert_called_once()
