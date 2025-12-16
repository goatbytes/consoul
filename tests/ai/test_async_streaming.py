"""Tests for async AI response streaming functionality."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from consoul.ai.async_streaming import StreamEvent, async_stream_events
from consoul.ai.exceptions import StreamingError


def create_mock_chunk(content: str, tool_call_chunks: list | None = None) -> MagicMock:
    """Create a mock async streaming chunk with content.

    Args:
        content: Token content for the chunk
        tool_call_chunks: Optional tool call chunk data

    Returns:
        Mock chunk object with content and tool_call_chunks attributes
    """
    chunk = MagicMock()
    chunk.content = content
    chunk.tool_call_chunks = tool_call_chunks or []
    return chunk


def create_mock_chunks(tokens: list[str]) -> list[MagicMock]:
    """Create list of mock streaming chunks.

    Args:
        tokens: List of token strings

    Returns:
        List of mock chunk objects
    """
    return [create_mock_chunk(token) for token in tokens]


async def async_generator(items: list):
    """Helper to create async generator from list."""
    for item in items:
        yield item


class TestStreamEvent:
    """Tests for StreamEvent model."""

    def test_stream_event_token(self):
        """Test creating token event."""
        event = StreamEvent(type="token", data={"text": "Hello"})
        assert event.type == "token"
        assert event.data["text"] == "Hello"

    def test_stream_event_tool_call(self):
        """Test creating tool_call event."""
        event = StreamEvent(
            type="tool_call",
            data={
                "name": "bash_execute",
                "args": {"command": "ls"},
                "id": "call_123",
            },
        )
        assert event.type == "tool_call"
        assert event.data["name"] == "bash_execute"
        assert event.data["args"]["command"] == "ls"
        assert event.data["id"] == "call_123"

    def test_stream_event_done(self):
        """Test creating done event."""
        from langchain_core.messages import AIMessage

        msg = AIMessage(content="Complete response")
        event = StreamEvent(
            type="done", data={"message": msg, "text": "Complete response"}
        )
        assert event.type == "done"
        assert event.data["message"].content == "Complete response"
        assert event.data["text"] == "Complete response"


class TestAsyncStreamEvents:
    """Tests for async_stream_events function."""

    @pytest.mark.asyncio
    async def test_basic_token_streaming(self):
        """Test basic async token streaming."""
        mock_model = MagicMock()
        mock_model.astream = MagicMock(
            return_value=async_generator(create_mock_chunks(["Hello", " ", "world"]))
        )

        messages = [{"role": "user", "content": "Hi"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        # Should have 3 token events + 1 done event
        assert len(events) == 4

        # Check token events
        assert events[0].type == "token"
        assert events[0].data["text"] == "Hello"
        assert events[1].type == "token"
        assert events[1].data["text"] == " "
        assert events[2].type == "token"
        assert events[2].data["text"] == "world"

        # Check done event
        assert events[3].type == "done"
        assert events[3].data["text"] == "Hello world"
        assert events[3].data["message"].content == "Hello world"

    @pytest.mark.asyncio
    async def test_streaming_with_empty_chunks(self):
        """Test streaming with empty chunks (metadata chunks)."""
        mock_model = MagicMock()
        chunks = [
            create_mock_chunk("Hello"),
            create_mock_chunk(""),  # Empty - should not yield token event
            create_mock_chunk(" world"),
        ]
        mock_model.astream = MagicMock(return_value=async_generator(chunks))

        messages = [{"role": "user", "content": "Hi"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        # Should have 2 token events + 1 done event (empty chunk skipped)
        assert len(events) == 3
        assert events[0].data["text"] == "Hello"
        assert events[1].data["text"] == " world"
        assert events[2].type == "done"
        assert events[2].data["text"] == "Hello world"

    @pytest.mark.asyncio
    async def test_streaming_with_tool_calls(self):
        """Test streaming with tool call chunks."""
        mock_model = MagicMock()

        # Create chunks with tool_call_chunks data
        chunks = [
            create_mock_chunk(
                "", [{"index": 0, "name": "bash_execute", "id": "call_1", "args": ""}]
            ),
            create_mock_chunk("", [{"index": 0, "args": '{"'}]),
            create_mock_chunk("", [{"index": 0, "args": "command"}]),
            create_mock_chunk("", [{"index": 0, "args": '":"'}]),
            create_mock_chunk("", [{"index": 0, "args": "ls"}]),
            create_mock_chunk("", [{"index": 0, "args": '"}'}]),
        ]
        mock_model.astream = MagicMock(return_value=async_generator(chunks))

        messages = [{"role": "user", "content": "List files"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        # Should have 1 tool_call event + 1 done event (no token events for empty content)
        assert len(events) == 2

        # Check tool_call event
        assert events[0].type == "tool_call"
        assert events[0].data["name"] == "bash_execute"
        assert events[0].data["args"]["command"] == "ls"
        assert events[0].data["id"] == "call_1"

        # Check done event
        assert events[1].type == "done"
        assert len(events[1].data["message"].tool_calls) == 1

    @pytest.mark.asyncio
    async def test_streaming_with_content_and_tool_calls(self):
        """Test streaming with both content and tool calls."""
        mock_model = MagicMock()

        # Create chunks with both content and tool calls
        chunks = [
            create_mock_chunk("I'll list the files for you."),
            create_mock_chunk(
                "", [{"index": 0, "name": "bash_execute", "id": "call_1", "args": ""}]
            ),
            create_mock_chunk("", [{"index": 0, "args": '{"command":"ls"}'}]),
        ]
        mock_model.astream = MagicMock(return_value=async_generator(chunks))

        messages = [{"role": "user", "content": "List files"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        # Should have 1 token event + 1 tool_call event + 1 done event
        assert len(events) == 3

        assert events[0].type == "token"
        assert events[0].data["text"] == "I'll list the files for you."

        assert events[1].type == "tool_call"
        assert events[1].data["name"] == "bash_execute"

        assert events[2].type == "done"
        assert events[2].data["text"] == "I'll list the files for you."

    @pytest.mark.asyncio
    async def test_streaming_keyboard_interrupt(self):
        """Test graceful handling of keyboard interrupt."""
        mock_model = MagicMock()

        async def stream_with_interrupt(messages):
            """Generator that raises KeyboardInterrupt mid-stream."""
            yield create_mock_chunk("Hello")
            yield create_mock_chunk(" partial")
            raise KeyboardInterrupt()

        mock_model.astream = MagicMock(side_effect=stream_with_interrupt)

        messages = [{"role": "user", "content": "Hi"}]

        with pytest.raises(StreamingError) as exc_info:
            async for _ in async_stream_events(mock_model, messages):
                pass

        # Verify partial response is preserved
        error = exc_info.value
        assert error.partial_response == "Hello partial"
        assert "interrupted by user" in str(error).lower()

    @pytest.mark.asyncio
    async def test_streaming_error_handling(self):
        """Test handling of streaming errors with partial response preservation."""
        mock_model = MagicMock()

        async def stream_with_error(messages):
            """Generator that raises error mid-stream."""
            yield create_mock_chunk("Partial")
            yield create_mock_chunk(" response")
            raise RuntimeError("Network error")

        mock_model.astream = MagicMock(side_effect=stream_with_error)

        messages = [{"role": "user", "content": "Hi"}]

        with pytest.raises(StreamingError) as exc_info:
            async for _ in async_stream_events(mock_model, messages):
                pass

        # Verify partial response is preserved
        error = exc_info.value
        assert error.partial_response == "Partial response"
        assert "Network error" in str(error)

    @pytest.mark.asyncio
    async def test_streaming_empty_response(self):
        """Test streaming with no content (all empty chunks)."""
        mock_model = MagicMock()
        chunks = [
            create_mock_chunk(""),
            create_mock_chunk(""),
        ]
        mock_model.astream = MagicMock(return_value=async_generator(chunks))

        messages = [{"role": "user", "content": "Hi"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        # Should only have done event (no token events)
        assert len(events) == 1
        assert events[0].type == "done"
        assert events[0].data["text"] == ""
        assert events[0].data["message"].content == ""

    @pytest.mark.asyncio
    async def test_streaming_multiline_content(self):
        """Test streaming with newlines."""
        mock_model = MagicMock()
        tokens = ["Line 1", "\n", "Line 2", "\n", "Line 3"]
        mock_model.astream = MagicMock(
            return_value=async_generator(create_mock_chunks(tokens))
        )

        messages = [{"role": "user", "content": "Multiple lines"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        # Should have 5 token events + 1 done event
        assert len(events) == 6

        # Verify content
        token_events = [e for e in events if e.type == "token"]
        full_text = "".join(e.data["text"] for e in token_events)
        assert full_text == "Line 1\nLine 2\nLine 3"
        assert full_text.count("\n") == 2

        # Verify done event
        done_event = events[-1]
        assert done_event.type == "done"
        assert done_event.data["text"] == "Line 1\nLine 2\nLine 3"

    @pytest.mark.asyncio
    async def test_streaming_special_characters(self):
        """Test streaming with special characters."""
        mock_model = MagicMock()
        tokens = ["Hello", " 👋", " ", "world", " ", "🌍"]
        mock_model.astream = MagicMock(
            return_value=async_generator(create_mock_chunks(tokens))
        )

        messages = [{"role": "user", "content": "Emoji test"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        # Verify emojis are preserved
        token_events = [e for e in events if e.type == "token"]
        full_text = "".join(e.data["text"] for e in token_events)
        assert full_text == "Hello 👋 world 🌍"
        assert "👋" in full_text
        assert "🌍" in full_text

    @pytest.mark.asyncio
    async def test_streaming_multiple_tool_calls(self):
        """Test streaming with multiple tool calls."""
        mock_model = MagicMock()

        # Create chunks with multiple tool calls
        chunks = [
            create_mock_chunk(
                "", [{"index": 0, "name": "tool1", "id": "call_1", "args": '{"a":1}'}]
            ),
            create_mock_chunk(
                "", [{"index": 1, "name": "tool2", "id": "call_2", "args": '{"b":2}'}]
            ),
        ]
        mock_model.astream = MagicMock(return_value=async_generator(chunks))

        messages = [{"role": "user", "content": "Test"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        # Should have 2 tool_call events + 1 done event
        assert len(events) == 3

        assert events[0].type == "tool_call"
        assert events[0].data["name"] == "tool1"
        assert events[0].data["args"]["a"] == 1

        assert events[1].type == "tool_call"
        assert events[1].data["name"] == "tool2"
        assert events[1].data["args"]["b"] == 2

        assert events[2].type == "done"
        assert len(events[2].data["message"].tool_calls) == 2

    @pytest.mark.asyncio
    async def test_streaming_immediate_error(self):
        """Test error before any tokens are received."""
        mock_model = MagicMock()

        async def stream_immediate_error(messages):
            """Raise error before yielding any tokens."""
            raise ConnectionError("Connection failed")
            yield  # Make it a generator (unreachable)

        mock_model.astream = MagicMock(side_effect=stream_immediate_error)

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(StreamingError) as exc_info:
            async for _ in async_stream_events(mock_model, messages):
                pass

        # Verify empty partial response
        error = exc_info.value
        assert error.partial_response == ""
        assert "Connection failed" in str(error)

    @pytest.mark.asyncio
    async def test_event_sequence_order(self):
        """Test that events are yielded in the correct order."""
        mock_model = MagicMock()

        # Create a realistic sequence: tokens, then tool call, then more tokens
        chunks = [
            create_mock_chunk("Let me"),
            create_mock_chunk(" check"),
            create_mock_chunk(
                "", [{"index": 0, "name": "bash", "id": "1", "args": '{"cmd":"ls"}'}]
            ),
            create_mock_chunk(" that"),
        ]
        mock_model.astream = MagicMock(return_value=async_generator(chunks))

        messages = [{"role": "user", "content": "Test"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        # Verify sequence: token, token, token, tool_call, done
        assert events[0].type == "token"
        assert events[0].data["text"] == "Let me"

        assert events[1].type == "token"
        assert events[1].data["text"] == " check"

        assert events[2].type == "token"
        assert events[2].data["text"] == " that"

        # Tool call event should be after all tokens
        assert events[3].type == "tool_call"
        assert events[3].data["name"] == "bash"

        # Done event should be last
        assert events[4].type == "done"
        assert events[4].data["text"] == "Let me check that"


class TestAsyncStreamingIntegration:
    """Integration tests comparing async_stream_events with stream_response."""

    @pytest.mark.asyncio
    async def test_consistency_with_sync_streaming(self):
        """Test that async streaming produces the same result as sync streaming."""
        from consoul.ai.streaming import _reconstruct_ai_message

        # Create identical chunks for both functions
        chunks = create_mock_chunks(["Hello", " ", "world"])

        # Test _reconstruct_ai_message directly (shared logic)
        reconstructed = _reconstruct_ai_message(chunks)
        assert reconstructed.content == "Hello world"
        assert reconstructed.tool_calls == []

        # Test async streaming produces same final result
        mock_model = MagicMock()
        mock_model.astream = MagicMock(return_value=async_generator(chunks))

        messages = [{"role": "user", "content": "Hi"}]
        events = []

        async for event in async_stream_events(mock_model, messages):
            events.append(event)

        done_event = events[-1]
        assert done_event.data["message"].content == "Hello world"
        assert done_event.data["message"].tool_calls == []
