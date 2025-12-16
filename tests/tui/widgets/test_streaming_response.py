"""Tests for StreamingResponse widget."""

from __future__ import annotations

import asyncio
import time

import pytest
from textual.app import App, ComposeResult

from consoul.tui.widgets.streaming_response import StreamingResponse

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class StreamingResponseTestApp(App[None]):
    """Test app for StreamingResponse widget."""

    def __init__(self, renderer: str = "markdown") -> None:
        """Initialize test app with specified renderer mode.

        Args:
            renderer: Rendering mode to use
        """
        super().__init__()
        self.renderer = renderer

    def compose(self) -> ComposeResult:
        """Compose test app with StreamingResponse."""
        yield StreamingResponse(renderer=self.renderer)


class TestStreamingResponseInitialization:
    """Test StreamingResponse initialization and basic properties."""

    async def test_streaming_response_mounts(self) -> None:
        """Test StreamingResponse can be mounted and has correct initial state."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)
            assert widget.border_title == "Assistant"
            assert widget.token_count == 0
            assert widget.streaming is False
            assert widget.renderer_mode == "markdown"
            assert widget.full_content == ""
            assert len(widget.token_buffer) == 0

    async def test_streaming_response_with_different_renderers(self) -> None:
        """Test StreamingResponse can be initialized with different renderers."""
        for renderer in ["markdown", "richlog", "hybrid"]:
            app = StreamingResponseTestApp(renderer=renderer)
            async with app.run_test():
                widget = app.query_one(StreamingResponse)
                assert widget.renderer_mode == renderer

    async def test_streaming_response_has_correct_css_class(self) -> None:
        """Test StreamingResponse has the correct CSS class."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)
            assert widget.has_class("streaming-response")


class TestStreamingResponseTokenManagement:
    """Test adding tokens and buffering behavior."""

    async def test_add_single_token(self) -> None:
        """Test adding a single token to StreamingResponse."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            await widget.add_token("Hello")
            await pilot.pause()

            assert widget.token_count == 1
            assert widget.streaming is True
            assert "Hello" in widget.full_content

    async def test_add_multiple_tokens(self) -> None:
        """Test adding multiple tokens increments counter correctly."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            tokens = ["Hello", " ", "world", "!"]
            for token in tokens:
                await widget.add_token(token)
                await pilot.pause()

            assert widget.token_count == 4
            assert widget.streaming is True
            assert widget.full_content == "Hello world!"

    async def test_buffer_threshold_triggers_render(self) -> None:
        """Test rendering when buffer threshold reached."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Add enough tokens to exceed buffer (200 chars)
            long_text = "x" * 250
            await widget.add_token(long_text)
            await pilot.pause()

            # Should have rendered (buffer cleared)
            assert widget.last_render_time > 0
            assert len(widget.token_buffer) == 0

    async def test_debounce_triggers_render(self) -> None:
        """Test rendering when debounce time elapsed."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Add small token
            await widget.add_token("Test")
            await pilot.pause()

            # Wait for debounce time to elapse
            await asyncio.sleep(0.2)  # 200ms > 150ms debounce

            # Add another token - should trigger render
            await widget.add_token(" message")
            await pilot.pause()

            assert widget.last_render_time > 0


class TestStreamingResponseFinalization:
    """Test finalizing and resetting streams."""

    async def test_finalize_stream(self) -> None:
        """Test finalizing stream updates state and border title."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Add some tokens
            await widget.add_token("Test")
            await widget.add_token(" message")
            await pilot.pause()

            assert widget.streaming is True

            # Finalize stream
            await widget.finalize_stream()
            await pilot.pause()

            assert widget.streaming is False
            assert "2 tokens" in widget.border_title

    async def test_finalize_updates_border_title_with_token_count(self) -> None:
        """Test border title shows correct token count after finalization."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Add 5 tokens
            for i in range(5):
                await widget.add_token(f"token{i} ")
                await pilot.pause()

            await widget.finalize_stream()
            await pilot.pause()

            assert widget.border_title == "Assistant (5 tokens)"

    async def test_reset_clears_state(self) -> None:
        """Test reset clears all state and content."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Add tokens and finalize
            await widget.add_token("Hello world")
            await widget.finalize_stream()
            await pilot.pause()

            assert widget.token_count > 0
            assert widget.full_content != ""

            # Reset
            widget.reset()
            await pilot.pause()

            assert widget.token_count == 0
            assert widget.full_content == ""
            assert widget.streaming is False
            assert len(widget.token_buffer) == 0
            assert widget.border_title == "Assistant"
            assert widget.last_render_time == 0.0

    async def test_reset_after_finalize(self) -> None:
        """Test reset works correctly after stream finalization."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Stream, finalize, then reset
            await widget.add_token("Test")
            await widget.finalize_stream()
            await pilot.pause()

            widget.reset()
            await pilot.pause()

            # Should be back to initial state
            assert widget.border_title == "Assistant"
            assert widget.token_count == 0
            assert not widget.streaming


class TestStreamingResponseRendererModes:
    """Test different renderer modes."""

    async def test_markdown_renderer(self) -> None:
        """Test markdown renderer mode."""
        app = StreamingResponseTestApp(renderer="markdown")
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            await widget.add_token("# Hello")
            await widget.add_token("\n\n")
            await widget.add_token("**Bold text**")
            await pilot.pause()

            assert widget.renderer_mode == "markdown"
            assert "Hello" in widget.full_content
            assert "Bold text" in widget.full_content

    async def test_richlog_renderer(self) -> None:
        """Test richlog renderer mode (plain text)."""
        app = StreamingResponseTestApp(renderer="richlog")
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            await widget.add_token("Plain text")
            await pilot.pause()

            assert widget.renderer_mode == "richlog"
            assert widget.full_content == "Plain text"

    async def test_hybrid_renderer(self) -> None:
        """Test hybrid renderer mode."""
        app = StreamingResponseTestApp(renderer="hybrid")
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            await widget.add_token("# Test")
            await pilot.pause()

            assert widget.renderer_mode == "hybrid"
            assert widget.full_content == "# Test"

    async def test_markdown_fallback_on_error(self) -> None:
        """Test markdown falls back to plain text on rendering error."""
        app = StreamingResponseTestApp(renderer="markdown")
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Add token and force markdown failure flag
            await widget.add_token("Test")
            widget._markdown_failed = True
            await widget.add_token(" content")
            await pilot.pause()

            # Should still work with plain text fallback
            assert widget.full_content == "Test content"


class TestStreamingResponsePerformance:
    """Test performance with large token streams."""

    async def test_stream_1000_tokens_performance(self) -> None:
        """Test streaming 1000 tokens completes in reasonable time."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            start = time.time()

            # Stream 1000 tokens
            for i in range(1000):
                await widget.add_token("token ")
                if i % 100 == 0:
                    await pilot.pause()

            await widget.finalize_stream()
            await pilot.pause()

            elapsed = time.time() - start

            # Should complete in under 2 seconds
            assert elapsed < 2.0
            assert widget.token_count == 1000

    async def test_long_content_doesnt_freeze(self) -> None:
        """Test that long content doesn't freeze the widget."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Add very long content
            long_content = "Lorem ipsum " * 1000
            await widget.add_token(long_content)
            await pilot.pause()

            # Should still be responsive
            assert widget.streaming is True
            assert len(widget.full_content) > 10000


class TestStreamingResponseReactiveProperties:
    """Test reactive property behavior."""

    async def test_streaming_reactive_updates(self) -> None:
        """Test that streaming reactive property updates correctly."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Initially not streaming
            assert widget.streaming is False

            # Add token - should set streaming to True
            await widget.add_token("Test")
            await pilot.pause()

            assert widget.streaming is True

            # Finalize - should set streaming to False
            await widget.finalize_stream()
            await pilot.pause()

            assert widget.streaming is False

    async def test_token_count_reactive_updates(self) -> None:
        """Test that token_count reactive property updates correctly."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            initial_count = widget.token_count
            assert initial_count == 0

            # Add tokens
            for i in range(5):
                await widget.add_token(f"token{i}")
                await pilot.pause()
                assert widget.token_count == i + 1

    async def test_streaming_watch_updates_css_class(self) -> None:
        """Test that streaming state updates CSS class."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Initially no streaming class
            assert not widget.has_class("streaming")

            # Add token - should add streaming class
            await widget.add_token("Test")
            await pilot.pause()

            assert widget.has_class("streaming")

            # Finalize - should remove streaming class
            await widget.finalize_stream()
            await pilot.pause()

            assert not widget.has_class("streaming")


class TestStreamingResponseBorderTitle:
    """Test border title updates."""

    async def test_initial_border_title(self) -> None:
        """Test initial border title is 'Assistant'."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)
            assert widget.border_title == "Assistant"

    async def test_border_title_during_streaming(self) -> None:
        """Test border title remains 'Assistant' during streaming."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            await widget.add_token("Streaming...")
            await pilot.pause()

            assert widget.border_title == "Assistant"

    async def test_border_title_after_finalization(self) -> None:
        """Test border title updates with token count after finalization."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            for _ in range(10):
                await widget.add_token("token ")

            await widget.finalize_stream()
            await pilot.pause()

            assert widget.border_title == "Assistant (10 tokens)"

    async def test_border_title_resets(self) -> None:
        """Test border title resets after reset()."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            await widget.add_token("Test")
            await widget.finalize_stream()
            await pilot.pause()

            assert "tokens" in widget.border_title

            widget.reset()
            await pilot.pause()

            assert widget.border_title == "Assistant"


class TestStreamingResponseBugFixes:
    """Test fixes for reported bugs."""

    async def test_finalize_renders_without_cursor_after_buffer_flush(self) -> None:
        """Test that finalize_stream() renders final state even after buffer is flushed.

        Regression test: After buffer is flushed, finalize_stream() should still
        render the final content without the cursor, not skip rendering due to
        empty buffer.
        """
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Add enough tokens to trigger buffer flush
            long_text = "x" * 250
            await widget.add_token(long_text)
            await pilot.pause()

            # Buffer should be empty after flush
            assert len(widget.token_buffer) == 0
            assert widget.streaming is True

            # Finalize should still render (force=True)
            await widget.finalize_stream()
            await pilot.pause()

            # Should be finalized
            assert widget.streaming is False
            assert "tokens" in widget.border_title

    async def test_markdown_mode_shows_cursor_during_streaming(self) -> None:
        """Test that markdown renderer shows cursor during streaming.

        Regression test: The cursor should be visible when using markdown renderer,
        using rich.console.Group to combine markdown and cursor.
        """
        app = StreamingResponseTestApp(renderer="markdown")
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Add markdown content
            await widget.add_token("# Hello")
            await widget.add_token("\n\n**Bold**")

            # Force a render with enough content
            await widget.add_token(" " * 200)
            await pilot.pause()

            # Widget should be streaming
            assert widget.streaming is True

            # The internal renderable should include cursor via Group
            # (we can't easily inspect the rendered output in tests,
            # but we verify the code path is executed without error)

    async def test_finalize_after_immediate_flush(self) -> None:
        """Test finalize works correctly when called right after a flush."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Trigger immediate flush with large content
            await widget.add_token("x" * 300)
            await pilot.pause()

            # Buffer is now empty, but streaming=True
            assert len(widget.token_buffer) == 0
            assert widget.streaming is True

            # Finalize immediately - should not skip render
            await widget.finalize_stream()
            await pilot.pause()

            assert widget.streaming is False
            assert widget.border_title == "Assistant (1 tokens)"


class TestStreamingResponseThinkingDetection:
    """Test thinking/reasoning detection functionality."""

    async def test_detect_thinking_start_with_think_tag(self) -> None:
        """Test detection of <think> tag at start of content."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            assert widget.detect_thinking_start("<think>Let me analyze...") is True
            assert widget.detect_thinking_start("  <think>Let me analyze...") is True
            assert widget.detect_thinking_start("\n<think>Let me analyze...") is True

    async def test_detect_thinking_start_with_thinking_tag(self) -> None:
        """Test detection of <thinking> tag at start of content."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            assert widget.detect_thinking_start("<thinking>Step 1...") is True
            assert widget.detect_thinking_start("  <thinking>Step 1...") is True

    async def test_detect_thinking_start_with_reasoning_tag(self) -> None:
        """Test detection of <reasoning> tag at start of content."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            assert widget.detect_thinking_start("<reasoning>First, consider...") is True

    async def test_detect_thinking_start_case_insensitive(self) -> None:
        """Test thinking detection is case-insensitive."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            assert widget.detect_thinking_start("<THINK>Analysis...") is True
            assert widget.detect_thinking_start("<Think>Analysis...") is True
            assert widget.detect_thinking_start("<THINKING>Step 1...") is True

    async def test_detect_thinking_start_returns_false_for_non_thinking(self) -> None:
        """Test detection returns False for normal content."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            assert widget.detect_thinking_start("The answer is 42") is False
            assert widget.detect_thinking_start("Let me think about this...") is False
            assert widget.detect_thinking_start("  Normal content") is False

    async def test_detect_thinking_start_returns_false_for_tag_not_at_start(
        self,
    ) -> None:
        """Test detection returns False when tag is not at start."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            assert widget.detect_thinking_start("Here is my <think>...") is False
            assert widget.detect_thinking_start("Answer: <thinking>...") is False

    async def test_detect_thinking_end_with_closing_tags(self) -> None:
        """Test detection of closing tags in thinking buffer."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            # Set up thinking buffer with closing tag
            widget.thinking_buffer = "<think>Step 1: Analyze\nStep 2: Conclude</think>"
            assert widget.detect_thinking_end() is True

            widget.thinking_buffer = "<thinking>My reasoning</thinking>"
            assert widget.detect_thinking_end() is True

            widget.thinking_buffer = "<reasoning>First, then</reasoning>"
            assert widget.detect_thinking_end() is True

    async def test_detect_thinking_end_case_insensitive(self) -> None:
        """Test thinking end detection is case-insensitive."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            widget.thinking_buffer = "<think>Analysis</THINK>"
            assert widget.detect_thinking_end() is True

            widget.thinking_buffer = "<thinking>Step 1</Thinking>"
            assert widget.detect_thinking_end() is True

    async def test_detect_thinking_end_returns_false_without_closing(self) -> None:
        """Test detection returns False when no closing tag present."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            widget.thinking_buffer = "<think>Still analyzing..."
            assert widget.detect_thinking_end() is False

            widget.thinking_buffer = "<thinking>Step 1\nStep 2\nStep 3"
            assert widget.detect_thinking_end() is False

    async def test_in_thinking_mode_reactive_property(self) -> None:
        """Test in_thinking_mode reactive property exists and updates."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Initially not in thinking mode
            assert widget.in_thinking_mode is False

            # Set to thinking mode
            widget.in_thinking_mode = True
            await pilot.pause()

            assert widget.in_thinking_mode is True

    async def test_thinking_mode_updates_border_title(self) -> None:
        """Test border title updates when in_thinking_mode changes."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Initially normal border title
            assert widget.border_title == "Assistant"

            # Enter thinking mode
            widget.in_thinking_mode = True
            await pilot.pause()

            assert widget.border_title == "🧠 Thinking"

            # Exit thinking mode
            widget.in_thinking_mode = False
            await pilot.pause()

            assert widget.border_title == "Assistant"

    async def test_thinking_buffer_initialization(self) -> None:
        """Test thinking_buffer is initialized empty."""
        app = StreamingResponseTestApp()
        async with app.run_test():
            widget = app.query_one(StreamingResponse)

            assert widget.thinking_buffer == ""
            assert hasattr(widget, "_thinking_detected")
            assert widget._thinking_detected is False

    async def test_full_thinking_workflow(self) -> None:
        """Test complete thinking detection workflow."""
        app = StreamingResponseTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingResponse)

            # Simulate streaming thinking content
            thinking_content = "<think>Step 1: Analyze problem\nStep 2: Find solution</think>The answer is 42"

            # Check if content starts with thinking
            assert widget.detect_thinking_start(thinking_content) is True

            # Accumulate in buffer
            widget.thinking_buffer = thinking_content

            # Check if thinking has ended
            assert widget.detect_thinking_end() is True

            # Border title should update based on mode
            widget.in_thinking_mode = True
            await pilot.pause()
            assert "🧠" in widget.border_title

            widget.in_thinking_mode = False
            await pilot.pause()
            assert widget.border_title == "Assistant"
