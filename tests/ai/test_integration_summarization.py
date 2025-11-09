"""Integration tests for conversation summarization with ConversationHistory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.messages import SystemMessage

from consoul.ai.history import ConversationHistory
from consoul.ai.summarization import ConversationSummarizer


class TestConversationHistorySummarization:
    """Tests for summarization integration with ConversationHistory."""

    def test_history_initialization_with_summarization_disabled(self):
        """Test that summarization is disabled by default."""
        history = ConversationHistory("gpt-4o", persist=False)

        assert history.summarize is False
        assert history._summarizer is None
        assert history.conversation_summary == ""

    def test_history_initialization_with_summarization_enabled_no_model(self):
        """Test that summarization requires a model instance."""
        with patch("consoul.ai.history.logger") as mock_logger:
            history = ConversationHistory(
                "gpt-4o",
                persist=False,
                summarize=True,  # No model instance provided
            )

            # Should be disabled due to missing model
            assert history.summarize is False
            assert history._summarizer is None

            # Should log a warning
            mock_logger.warning.assert_called_once()
            assert "requires a model instance" in str(mock_logger.warning.call_args)

    def test_history_initialization_with_summarization_enabled_with_model(self):
        """Test that summarization initializes correctly with model."""
        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100

        history = ConversationHistory(
            "gpt-4o", model=mock_model, persist=False, summarize=True
        )

        assert history.summarize is True
        assert history._summarizer is not None
        assert isinstance(history._summarizer, ConversationSummarizer)
        assert history.conversation_summary == ""

    def test_history_summarization_with_custom_params(self):
        """Test summarization with custom threshold and keep_recent."""
        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100

        history = ConversationHistory(
            "gpt-4o",
            model=mock_model,
            persist=False,
            summarize=True,
            summarize_threshold=5,
            keep_recent=2,
        )

        assert history._summarizer.threshold == 5
        assert history._summarizer.keep_recent == 2

    def test_history_summarization_with_separate_summary_model(self):
        """Test using separate model for summarization."""
        mock_main_model = MagicMock()
        mock_main_model.get_num_tokens_from_messages.return_value = 100

        mock_summary_model = MagicMock()

        history = ConversationHistory(
            "gpt-4o",
            model=mock_main_model,
            persist=False,
            summarize=True,
            summary_model=mock_summary_model,
        )

        assert history._summarizer.llm == mock_main_model
        assert history._summarizer.summary_model == mock_summary_model

    def test_get_trimmed_messages_without_summarization(self):
        """Test that get_trimmed_messages works normally without summarization."""
        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100

        history = ConversationHistory(
            "gpt-4o", model=mock_model, persist=False, summarize=False
        )

        # Add some messages
        history.add_user_message("Hello")
        history.add_assistant_message("Hi there!")

        with patch("consoul.ai.history.trim_messages") as mock_trim:
            mock_trim.return_value = history.messages.copy()
            result = history.get_trimmed_messages()

            # Should call standard trim_messages
            mock_trim.assert_called_once()
            assert len(result) == 2

    @patch("consoul.ai.history.create_token_counter")
    def test_get_trimmed_messages_below_summarization_threshold(
        self, mock_create_counter
    ):
        """Test that summarization is not triggered below threshold."""
        mock_counter = MagicMock(return_value=100)
        mock_create_counter.return_value = mock_counter

        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100

        history = ConversationHistory(
            "gpt-4o",
            model=mock_model,
            persist=False,
            summarize=True,
            summarize_threshold=10,
        )

        # Add 5 messages (below threshold)
        for i in range(5):
            history.add_user_message(f"Message {i}")

        with patch("consoul.ai.history.trim_messages") as mock_trim:
            mock_trim.return_value = history.messages.copy()
            result = history.get_trimmed_messages()

            # Should use standard trimming, not summarization
            mock_trim.assert_called_once()
            assert len(result) == 5

    @patch("consoul.ai.history.create_token_counter")
    def test_get_trimmed_messages_above_summarization_threshold(
        self, mock_create_counter
    ):
        """Test that summarization is triggered above threshold."""
        mock_counter = MagicMock(return_value=100)
        mock_create_counter.return_value = mock_counter

        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100

        # Mock summary generation
        mock_summary_response = MagicMock()
        mock_summary_response.content = "Summary of first 5 messages"
        mock_model.invoke.return_value = mock_summary_response

        history = ConversationHistory(
            "gpt-4o",
            model=mock_model,
            persist=False,
            summarize=True,
            summarize_threshold=5,
            keep_recent=2,
        )

        # Add 8 messages (above threshold)
        for i in range(8):
            history.add_user_message(f"Question {i}")
            history.add_assistant_message(f"Answer {i}")

        result = history.get_trimmed_messages()

        # Should return: summary + 2 recent messages = 3 total
        assert len(result) == 3
        assert isinstance(result[0], SystemMessage)
        assert "Summary of first 5 messages" in result[0].content
        assert result[1].content == "Question 7"
        assert result[2].content == "Answer 7"

        # Verify summary was stored
        assert history.conversation_summary == "Summary of first 5 messages"

    @patch("consoul.ai.history.create_token_counter")
    def test_get_trimmed_messages_preserves_system_message(self, mock_create_counter):
        """Test that system message is preserved during summarization."""
        mock_counter = MagicMock(return_value=100)
        mock_create_counter.return_value = mock_counter

        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100

        mock_summary_response = MagicMock()
        mock_summary_response.content = "Summary"
        mock_model.invoke.return_value = mock_summary_response

        history = ConversationHistory(
            "gpt-4o",
            model=mock_model,
            persist=False,
            summarize=True,
            summarize_threshold=5,
            keep_recent=2,
        )

        # Add system message and regular messages
        history.add_system_message("You are a helpful assistant")
        for i in range(8):
            history.add_user_message(f"Message {i}")

        result = history.get_trimmed_messages()

        # Should have: system message + summary + recent messages
        assert len(result) >= 3
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are a helpful assistant"
        assert isinstance(result[1], SystemMessage)
        assert "Summary" in result[1].content

    @patch("consoul.ai.history.create_token_counter")
    def test_get_trimmed_messages_progressive_summarization(self, mock_create_counter):
        """Test that summaries are progressively updated."""
        mock_counter = MagicMock(return_value=100)
        mock_create_counter.return_value = mock_counter

        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100

        # First summary
        first_summary = MagicMock()
        first_summary.content = "First summary"

        # Second summary (should include first)
        second_summary = MagicMock()
        second_summary.content = "Updated summary"

        mock_model.invoke.side_effect = [first_summary, second_summary]

        history = ConversationHistory(
            "gpt-4o",
            model=mock_model,
            persist=False,
            summarize=True,
            summarize_threshold=5,
            keep_recent=2,
        )

        # First batch - trigger first summary
        for i in range(6):
            history.add_user_message(f"Message {i}")

        _ = history.get_trimmed_messages()
        assert history.conversation_summary == "First summary"

        # Second batch - should update summary
        for i in range(6, 12):
            history.add_user_message(f"Message {i}")

        _ = history.get_trimmed_messages()
        assert history.conversation_summary == "Updated summary"

        # Verify second summary call included first summary
        second_call = mock_model.invoke.call_args_list[1]
        prompt_content = second_call[0][0][0].content
        assert "First summary" in prompt_content

    @patch("consoul.ai.history.create_token_counter")
    def test_get_trimmed_messages_summarization_error_fallback(
        self, mock_create_counter
    ):
        """Test fallback to standard trimming when summarization fails."""
        mock_counter = MagicMock(return_value=100)
        mock_create_counter.return_value = mock_counter

        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100
        mock_model.invoke.side_effect = Exception("API Error")

        history = ConversationHistory(
            "gpt-4o",
            model=mock_model,
            persist=False,
            summarize=True,
            summarize_threshold=5,
            keep_recent=2,
        )

        # Add messages above threshold
        for i in range(8):
            history.add_user_message(f"Message {i}")

        with patch("consoul.ai.history.trim_messages") as mock_trim:
            mock_trim.return_value = history.messages.copy()

            with patch("consoul.ai.history.logger") as mock_logger:
                result = history.get_trimmed_messages()

                # Should fall back to standard trimming
                mock_trim.assert_called_once()
                assert len(result) == 8

                # Should log warning
                mock_logger.warning.assert_called()

    @patch("consoul.ai.history.create_token_counter")
    def test_get_trimmed_messages_token_reduction(self, mock_create_counter):
        """Test that summarization actually reduces message count."""
        mock_counter = MagicMock(return_value=100)
        mock_create_counter.return_value = mock_counter

        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100

        mock_summary_response = MagicMock()
        mock_summary_response.content = "Concise summary"
        mock_model.invoke.return_value = mock_summary_response

        history = ConversationHistory(
            "gpt-4o",
            model=mock_model,
            persist=False,
            summarize=True,
            summarize_threshold=10,
            keep_recent=5,
        )

        # Add 20 messages
        for i in range(20):
            history.add_user_message(f"Message {i}")
            history.add_assistant_message(f"Response {i}")

        result = history.get_trimmed_messages()

        # Should significantly reduce message count
        # Original: 40 messages -> Result: 1 summary + 5 recent = 6 messages
        assert len(result) <= 10  # Much less than original 40
        assert len(result) >= 5  # At least keep_recent messages


class TestConversationHistoryBackwardCompatibility:
    """Tests to ensure backward compatibility when summarization is disabled."""

    @patch("consoul.ai.history.create_token_counter")
    def test_default_behavior_unchanged(self, mock_create_counter):
        """Test that default behavior is unchanged (summarization off)."""
        mock_counter = MagicMock(return_value=100)
        mock_create_counter.return_value = mock_counter

        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 100

        # Initialize without any summarization parameters
        history = ConversationHistory("gpt-4o", model=mock_model, persist=False)

        # Add many messages
        for i in range(50):
            history.add_user_message(f"Message {i}")

        with patch("consoul.ai.history.trim_messages") as mock_trim:
            mock_trim.return_value = history.messages.copy()
            _ = history.get_trimmed_messages()

            # Should use standard trimming only
            mock_trim.assert_called_once()
            assert history.summarize is False
            assert history._summarizer is None

    def test_all_history_methods_work_without_summarization(self):
        """Test that all ConversationHistory methods work without summarization."""
        history = ConversationHistory("gpt-4o", persist=False)

        # Test all basic methods
        history.add_system_message("System")
        history.add_user_message("User")
        history.add_assistant_message("Assistant")
        history.add_message("user", "Another user message")

        assert len(history) == 4
        assert history.count_tokens() >= 0

        messages = history.get_messages()
        assert len(messages) == 4

        dicts = history.get_messages_as_dicts()
        assert len(dicts) == 4

        history.clear()
        assert len(history) == 1  # System message preserved

        history.clear(preserve_system=False)
        assert len(history) == 0
