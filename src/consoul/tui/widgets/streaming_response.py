"""StreamingResponse widget for displaying real-time AI output.

This module provides a widget that handles streaming AI tokens with buffering,
debounced markdown rendering, and fallback strategies to prevent UI freezes.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

from textual.reactive import reactive
from textual.widgets import RichLog

__all__ = ["StreamingResponse"]

logger = logging.getLogger(__name__)


class StreamingResponse(RichLog):
    """Widget for displaying streaming AI responses.

    Buffers tokens and debounces markdown rendering for performance.
    Falls back to plain text if markdown rendering is too slow or fails.

    The widget implements three rendering modes:
    - markdown: Full markdown rendering with debouncing
    - richlog: Plain text streaming (faster)
    - hybrid: RichLog during streaming, Markdown on completion

    Attributes:
        streaming: Whether the widget is actively receiving tokens
        token_count: Number of tokens received
        renderer_mode: The rendering strategy to use
    """

    BUFFER_SIZE = 200  # characters
    DEBOUNCE_MS = 150  # milliseconds

    # Reactive state
    streaming: reactive[bool] = reactive(False)
    token_count: reactive[int] = reactive(0)
    in_thinking_mode: reactive[bool] = reactive(False)

    def __init__(
        self,
        renderer: Literal["markdown", "richlog", "hybrid"] = "markdown",
        **kwargs: Any,
    ) -> None:
        """Initialize StreamingResponse widget.

        Args:
            renderer: Rendering mode to use (markdown, richlog, or hybrid)
            **kwargs: Additional arguments passed to RichLog
        """
        super().__init__(wrap=True, markup=True, **kwargs)
        self.renderer_mode = renderer
        self.token_buffer: list[str] = []
        self.full_content = ""
        self.last_render_time = 0.0
        self._last_written_length = 0
        self.thinking_buffer = ""  # Buffer for detecting thinking tags
        self._thinking_detected = False  # Flag to track if we've detected thinking

    def on_mount(self) -> None:
        """Initialize streaming response widget on mount."""
        self.border_title = "Assistant"
        self.add_class("streaming-response")
        # Disable scrollbars since parent ChatView handles scrolling
        self.show_vertical_scrollbar = False
        self.show_horizontal_scrollbar = False
        # Set up a timer to continuously scroll parent during streaming
        # Use faster interval (50ms) for smoother scrolling
        # Store timer reference so we can stop it on finalize
        self._scroll_timer = self.set_interval(0.05, self._auto_scroll_parent)

    def _auto_scroll_parent(self) -> None:
        """Periodically scroll parent container during streaming.

        This timer runs continuously to keep the ChatView scrolled
        to the bottom as the streaming widget grows in height.
        """
        if self.streaming and self.parent and hasattr(self.parent, "scroll_end"):
            # Use call_after_refresh to avoid race conditions with layout
            self.parent.call_after_refresh(self.parent.scroll_end, animate=False)

    async def add_token(self, token: str) -> None:
        """Add a streaming token to the response.

        Tokens are buffered and rendered when either the buffer size
        threshold is reached or the debounce time has elapsed.

        Args:
            token: Text token from AI stream
        """
        self.token_buffer.append(token)
        self.full_content += token
        self.token_count += 1
        self.streaming = True

        # Check if we should render
        buffer_size = sum(len(t) for t in self.token_buffer)
        current_time = time.time() * 1000  # milliseconds
        time_since_render = current_time - self.last_render_time

        logger.debug(
            f"add_token: buffer_size={buffer_size}, time_since={time_since_render:.0f}ms, "
            f"total_len={len(self.full_content)}"
        )

        if buffer_size >= self.BUFFER_SIZE or time_since_render >= self.DEBOUNCE_MS:
            if self.full_content:
                logger.debug(
                    f"Rendering full content as markdown: {len(self.full_content)} chars"
                )
                # Clear and re-render the FULL content as markdown
                self.clear()
                from rich.markdown import Markdown

                try:
                    # Render the full content as markdown for proper formatting
                    md = Markdown(self.full_content)
                    self.write(md)
                except Exception as e:
                    # Fall back to plain text if markdown fails
                    logger.debug(f"Markdown render failed: {e}")
                    self.write(self.full_content)
                self._last_written_length = len(self.full_content)
                # Scroll to bottom to follow the streaming content
                self.scroll_end(animate=False)

                # Notify parent to scroll as our height changed
                # Use call_after_refresh to ensure layout is updated first
                if self.parent and hasattr(self.parent, "scroll_end"):
                    self.parent.call_after_refresh(
                        self.parent.scroll_end, animate=False
                    )

            self.token_buffer.clear()
            self.last_render_time = current_time

    async def finalize_stream(self) -> None:
        """Finalize streaming and render final content.

        Marks streaming as complete, renders any remaining buffered
        tokens, and updates the border title with token count.
        """
        self.streaming = False

        # Stop the auto-scroll timer to prevent race conditions
        if hasattr(self, "_scroll_timer") and self._scroll_timer:
            self._scroll_timer.stop()

        self.token_buffer.clear()
        # Write final content without cursor
        self.clear()
        self.write(self.full_content)
        self.border_title = f"Assistant ({self.token_count} tokens)"

        # Scroll self to bottom first (in case content is taller than viewport)
        self.scroll_end(animate=False)

        # Notify parent to scroll after final content render
        # Use animate=False to prevent animation drift causing scroll-up
        # scroll_end() already uses call_after_refresh internally for proper timing
        if self.parent and hasattr(self.parent, "scroll_end"):
            self.parent.scroll_end(animate=False)

    def reset(self) -> None:
        """Clear content and reset state.

        Removes all tokens and content, resets counters and flags,
        and clears the display.
        """
        self.token_buffer.clear()
        self.full_content = ""
        self.token_count = 0
        self.streaming = False
        self.last_render_time = 0.0
        self._last_written_length = 0
        self.clear()
        self.border_title = "Assistant"

    def watch_streaming(self, streaming: bool) -> None:
        """Update widget styling when streaming state changes.

        Called automatically when the streaming reactive property changes.

        Args:
            streaming: New streaming state
        """
        if streaming:
            self.add_class("streaming")
        else:
            self.remove_class("streaming")

    def detect_thinking_start(self, content: str) -> bool:
        """Detect if content starts with thinking/reasoning tags.

        Checks for common thinking tag patterns: <think>, <thinking>, <reasoning>

        Args:
            content: The content to check (usually first ~50 chars)

        Returns:
            True if thinking tags detected at start
        """
        content_lower = content.lower().lstrip()
        thinking_patterns = ["<think>", "<thinking>", "<reasoning>"]
        return any(content_lower.startswith(pattern) for pattern in thinking_patterns)

    def detect_thinking_end(self) -> bool:
        """Detect if thinking has ended by checking for closing tags.

        Returns:
            True if closing tag detected in thinking_buffer
        """
        buffer_lower = self.thinking_buffer.lower()
        closing_patterns = ["</think>", "</thinking>", "</reasoning>"]
        return any(pattern in buffer_lower for pattern in closing_patterns)

    def watch_in_thinking_mode(self, thinking: bool) -> None:
        """Update border title when thinking mode changes.

        Called automatically when the in_thinking_mode reactive property changes.

        Args:
            thinking: New thinking mode state
        """
        if thinking:
            self.border_title = "🧠 Thinking"
        else:
            self.border_title = "Assistant"
