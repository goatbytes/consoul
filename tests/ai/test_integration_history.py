"""Integration tests for conversation history with streaming and providers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from consoul.ai.history import ConversationHistory
from consoul.ai.streaming import stream_response


@pytest.mark.skip(reason="CLI-only streaming integration tests")
class TestHistoryStreamingIntegration:
    """Integration tests for conversation history with streaming."""

    @patch("consoul.ai.streaming.Live")
    @patch("consoul.ai.streaming.Console")
    def test_complete_conversation_flow(self, mock_console_class, mock_live_class):
        """Test complete flow: add messages → trim → stream response."""
        # Setup mocks
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_live = MagicMock()
        mock_live_class.return_value.__enter__ = MagicMock(return_value=mock_live)
        mock_live_class.return_value.__exit__ = MagicMock(return_value=False)

        # Create conversation history
        history = ConversationHistory("gpt-4o")
        history.add_system_message("You are a helpful assistant.")
        history.add_user_message("Hello!")

        # Setup streaming mock
        mock_model = MagicMock()

        def create_mock_chunk(content):
            chunk = MagicMock()
            chunk.content = content
            return chunk

        mock_model.stream.return_value = [
            create_mock_chunk("Hi"),
            create_mock_chunk(" there"),
            create_mock_chunk("!"),
        ]

        # Get trimmed messages for streaming
        trimmed_messages = history.get_trimmed_messages(reserve_tokens=1000)

        # Convert to dict format for streaming
        messages_dict = [
            {
                "role": msg.type if msg.type != "human" else "user",
                "content": msg.content,
            }
            for msg in trimmed_messages
        ]

        # Stream response (returns tuple of text and AIMessage)
        response, _ = stream_response(mock_model, messages_dict)

        # Add response to history
        history.add_assistant_message(response)

        # Verify complete conversation
        assert len(history) == 3  # system + user + assistant
        assert history.messages[0].content == "You are a helpful assistant."
        assert history.messages[1].content == "Hello!"
        assert history.messages[2].content == "Hi there!"

        # Verify streaming occurred
        assert mock_live.update.called

    def test_cross_provider_token_counting(self):
        """Test token counting consistency across providers."""

        # Create mock counter that returns predictable counts
        def mock_counter(messages):
            # Simple: 10 tokens per message
            return len(messages) * 10

        with patch("consoul.ai.context.create_token_counter") as mock_create_counter:
            mock_create_counter.return_value = mock_counter

            # Test with different providers
            providers = [
                ("gpt-4o", 128_000),
                ("claude-3-5-sonnet", 200_000),
                ("gemini-1.5-pro", 2_000_000),
            ]

            for model_name, expected_limit in providers:
                history = ConversationHistory(model_name)

                # Add same messages
                history.add_system_message("System")
                history.add_user_message("User")
                history.add_assistant_message("Assistant")

                # Token count should be consistent (mock returns same count)
                tokens = history.count_tokens()
                assert tokens == 30  # 3 messages x 10 tokens

                # But max_tokens should differ by provider
                assert history.max_tokens == expected_limit

                # Trimming should use provider's limit
                trimmed = history.get_trimmed_messages(reserve_tokens=1000)
                # All messages should fit (30 tokens << limit - 1000)
                assert len(trimmed) == 3
