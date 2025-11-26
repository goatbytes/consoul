"""Tests for AI response streaming functionality."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from consoul.ai.exceptions import StreamingError
from consoul.ai.streaming import stream_response


def create_mock_chunk(content: str) -> MagicMock:
    """Create a mock streaming chunk with content.

    Args:
        content: Token content for the chunk.

    Returns:
        Mock chunk object with content attribute and empty tool_call_chunks.
    """
    chunk = MagicMock()
    chunk.content = content
    chunk.tool_call_chunks = []  # No tool calls by default
    return chunk


def create_mock_chunks(tokens: list[str]) -> list[MagicMock]:
    """Create list of mock streaming chunks.

    Args:
        tokens: List of token strings.

    Returns:
        List of mock chunk objects.
    """
    return [create_mock_chunk(token) for token in tokens]


class TestStreamResponse:
    """Tests for stream_response function."""

    @patch("consoul.ai.streaming.Live")
    @patch("consoul.ai.streaming.Console")
    def test_stream_response_basic(self, mock_console_class, mock_live_class):
        """Test basic streaming functionality with spinner."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_live = MagicMock()
        mock_live_class.return_value.__enter__ = MagicMock(return_value=mock_live)
        mock_live_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_model = MagicMock()
        mock_model.stream.return_value = create_mock_chunks(["Hello", " ", "world"])

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(mock_model, messages)

        assert result_text == "Hello world"
        assert ai_message.content == "Hello world"
        assert ai_message.tool_calls == []
        mock_model.stream.assert_called_once_with(messages)

        # Verify Live display was used
        assert mock_live.update.called
        # Should have updated with response text
        update_calls = mock_live.update.call_args_list
        assert len(update_calls) > 0

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_basic_no_spinner(self, mock_console_class):
        """Test basic streaming functionality without spinner."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()
        mock_model.stream.return_value = create_mock_chunks(["Hello", " ", "world"])

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_spinner=False
        )

        assert result_text == "Hello world"
        assert ai_message.content == "Hello world"
        mock_model.stream.assert_called_once_with(messages)

        # Verify console output calls
        assert mock_console.print.called
        # Should have printed prefix
        # Check all print calls for the prefix
        printed_text = "".join(
            str(call.args[0]) if call.args else ""
            for call in mock_console.print.call_args_list
        )
        assert "Assistant: " in printed_text

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_with_empty_chunks(self, mock_console_class):
        """Test streaming with empty chunks (metadata chunks)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()
        # Include empty chunks that should be skipped
        chunks = [
            create_mock_chunk("Hello"),
            create_mock_chunk(""),  # Empty - should skip
            create_mock_chunk(" "),
            create_mock_chunk(""),  # Empty - should skip
            create_mock_chunk("world"),
        ]
        mock_model.stream.return_value = chunks

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_spinner=False
        )

        assert result_text == "Hello world"
        assert ai_message.content == "Hello world"
        # Empty chunks should not affect output
        mock_model.stream.assert_called_once_with(messages)

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_keyboard_interrupt(self, mock_console_class):
        """Test graceful handling of keyboard interrupt (Ctrl+C)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()

        def stream_with_interrupt(messages):
            """Generator that raises KeyboardInterrupt mid-stream."""
            yield create_mock_chunk("Hello")
            yield create_mock_chunk(" ")
            raise KeyboardInterrupt()

        mock_model.stream.side_effect = stream_with_interrupt

        messages = [{"role": "user", "content": "Hi"}]

        with pytest.raises(StreamingError) as exc_info:
            stream_response(mock_model, messages, show_spinner=False)

        # Should have printed interrupt message
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Interrupted" in call for call in print_calls)

        # Verify partial response is preserved
        error = exc_info.value
        assert error.partial_response == "Hello "
        assert "interrupted by user" in str(error).lower()

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_streaming_error(self, mock_console_class):
        """Test handling of streaming errors with partial response preservation."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()

        def stream_with_error(messages):
            """Generator that raises error mid-stream."""
            yield create_mock_chunk("Partial")
            yield create_mock_chunk(" response")
            raise RuntimeError("Network error")

        mock_model.stream.side_effect = stream_with_error

        messages = [{"role": "user", "content": "Hi"}]

        with pytest.raises(StreamingError) as exc_info:
            stream_response(mock_model, messages, show_spinner=False)

        # Verify partial response is preserved
        error = exc_info.value
        assert error.partial_response == "Partial response"
        assert "Network error" in str(error)

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_no_prefix(self, mock_console_class):
        """Test streaming without 'Assistant:' prefix."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()
        mock_model.stream.return_value = create_mock_chunks(["Hello"])

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_prefix=False, show_spinner=False
        )

        assert result_text == "Hello"
        assert ai_message.content == "Hello"

        # Verify "Assistant: " was not printed
        printed_text = "".join(
            str(call.args[0]) if call.args else ""
            for call in mock_console.print.call_args_list
        )
        assert "Assistant: " not in printed_text

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_custom_console(self, mock_console_class):
        """Test using custom console instance."""
        custom_console = MagicMock()

        mock_model = MagicMock()
        mock_model.stream.return_value = create_mock_chunks(["Test"])

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(
            mock_model, messages, console=custom_console, show_spinner=False
        )

        assert result_text == "Test"
        assert ai_message.content == "Test"
        # Should use custom console, not create new one
        mock_console_class.assert_not_called()
        assert custom_console.print.called

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_empty_response(self, mock_console_class):
        """Test streaming with no content (all empty chunks)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()
        mock_model.stream.return_value = [
            create_mock_chunk(""),
            create_mock_chunk(""),
        ]

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_spinner=False
        )

        assert result_text == ""
        assert ai_message.content == ""
        # Should not print prefix if no content
        printed_text = "".join(
            str(call.args[0]) if call.args else ""
            for call in mock_console.print.call_args_list
        )
        assert "Assistant: " not in printed_text

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_long_text(self, mock_console_class):
        """Test streaming with many tokens."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()
        # Simulate word-by-word streaming
        tokens = ["The", " ", "quick", " ", "brown", " ", "fox"]
        mock_model.stream.return_value = create_mock_chunks(tokens)

        messages = [{"role": "user", "content": "Tell me something"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_spinner=False
        )

        assert result_text == "The quick brown fox"
        assert ai_message.content == "The quick brown fox"
        mock_model.stream.assert_called_once()

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_multiline(self, mock_console_class):
        """Test streaming with newlines."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()
        tokens = ["Line 1", "\n", "Line 2", "\n", "Line 3"]
        mock_model.stream.return_value = create_mock_chunks(tokens)

        messages = [{"role": "user", "content": "Multiple lines"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_spinner=False
        )

        assert result_text == "Line 1\nLine 2\nLine 3"
        assert result_text.count("\n") == 2
        assert ai_message.content == result_text

    @patch("consoul.ai.streaming.Console")
    def test_stream_response_special_characters(self, mock_console_class):
        """Test streaming with special characters."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()
        tokens = ["Hello", " 👋", " ", "world", " ", "🌍"]
        mock_model.stream.return_value = create_mock_chunks(tokens)

        messages = [{"role": "user", "content": "Emoji test"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_spinner=False
        )

        assert result_text == "Hello 👋 world 🌍"
        assert "👋" in result_text
        assert "🌍" in result_text
        assert ai_message.content == result_text


class TestStreamingErrorPreservation:
    """Tests for partial response preservation during errors."""

    @patch("consoul.ai.streaming.Console")
    def test_partial_response_on_error(self, mock_console_class):
        """Test that partial response is preserved on any error."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()

        def stream_with_various_errors(messages):
            """Test different error types."""
            yield create_mock_chunk("Start")
            yield create_mock_chunk(" middle")
            raise ValueError("Some error")

        mock_model.stream.side_effect = stream_with_various_errors

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(StreamingError) as exc_info:
            stream_response(mock_model, messages, show_spinner=False)

        assert exc_info.value.partial_response == "Start middle"

    @patch("consoul.ai.streaming.Console")
    def test_empty_partial_response_on_immediate_error(self, mock_console_class):
        """Test error before any tokens are received."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()

        def stream_immediate_error(messages):
            """Raise error before yielding any tokens."""
            raise ConnectionError("Connection failed")

        mock_model.stream.side_effect = stream_immediate_error

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(StreamingError) as exc_info:
            stream_response(mock_model, messages, show_spinner=False)

        assert exc_info.value.partial_response == ""


class TestStreamingSpinner:
    """Tests for spinner progress indicator during streaming."""

    @patch("consoul.ai.streaming.Live")
    @patch("consoul.ai.streaming.Spinner")
    @patch("consoul.ai.streaming.Console")
    def test_spinner_shows_during_streaming(
        self, mock_console_class, mock_spinner_class, mock_live_class
    ):
        """Test that spinner is displayed during streaming with progress indicator."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_spinner = MagicMock()
        mock_spinner_class.return_value = mock_spinner

        mock_live = MagicMock()
        mock_live_class.return_value.__enter__ = MagicMock(return_value=mock_live)
        mock_live_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_model = MagicMock()
        mock_model.stream.return_value = create_mock_chunks(["Hello", " ", "world"])

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_spinner=True
        )

        assert result_text == "Hello world"
        assert ai_message.content == "Hello world"

        # Verify spinner was created
        mock_spinner_class.assert_called_once_with(
            "dots", text="Waiting for response..."
        )

        # Verify Live display was used with the spinner
        mock_live_class.assert_called_once()
        call_args = mock_live_class.call_args
        assert call_args[0][0] == mock_spinner  # First positional arg is the spinner
        assert call_args[1]["console"] == mock_console

        # Verify live.update was called with response text
        assert mock_live.update.called
        assert mock_live.update.call_count == 3  # Once for each token

    @patch("consoul.ai.streaming.Console")
    def test_spinner_disabled_fallback(self, mock_console_class):
        """Test fallback to simple printing when spinner is disabled."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_model = MagicMock()
        mock_model.stream.return_value = create_mock_chunks(["Test"])

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_spinner=False
        )

        assert result_text == "Test"
        assert ai_message.content == "Test"
        # Should use console.print directly, not Live
        assert mock_console.print.called

    @patch("consoul.ai.streaming.Live")
    @patch("consoul.ai.streaming.Console")
    def test_spinner_with_empty_chunks(self, mock_console_class, mock_live_class):
        """Test that empty chunks are skipped even with spinner enabled."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_live = MagicMock()
        mock_live_class.return_value.__enter__ = MagicMock(return_value=mock_live)
        mock_live_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_model = MagicMock()
        # Include empty chunks that should be skipped
        chunks = [
            create_mock_chunk("Hello"),
            create_mock_chunk(""),  # Empty - should skip
            create_mock_chunk(" world"),
        ]
        mock_model.stream.return_value = chunks

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_spinner=True
        )

        assert result_text == "Hello world"
        assert ai_message.content == "Hello world"
        # Should only update twice (for non-empty chunks)
        assert mock_live.update.call_count == 2

    @patch("consoul.ai.streaming.Live")
    @patch("consoul.ai.streaming.Console")
    def test_spinner_without_prefix(self, mock_console_class, mock_live_class):
        """Test spinner mode without showing Assistant prefix."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_live = MagicMock()
        mock_live_class.return_value.__enter__ = MagicMock(return_value=mock_live)
        mock_live_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_model = MagicMock()
        mock_model.stream.return_value = create_mock_chunks(["Test"])

        messages = [{"role": "user", "content": "Hi"}]
        result_text, ai_message = stream_response(
            mock_model, messages, show_prefix=False, show_spinner=True
        )

        assert result_text == "Test"
        assert ai_message.content == "Test"
        # Verify update was called
        assert mock_live.update.called
        # Check that update was called with Text object (not containing prefix)
        update_call = mock_live.update.call_args[0][0]
        # The Text object should not have "Assistant: " in it
        assert "Assistant:" not in str(update_call)
