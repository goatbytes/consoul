"""StreamingResponse widget for displaying real-time AI output.

This module provides a widget that handles streaming AI tokens with buffering,
debounced markdown rendering, and fallback strategies to prevent UI freezes.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

from rich.markdown import Markdown
from rich.text import Text
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

    def on_mount(self) -> None:
        """Initialize streaming response widget on mount."""
        self.border_title = "Assistant"
        self.add_class("streaming-response")
        # Set up a timer to continuously scroll parent during streaming
        self.set_interval(0.2, self._auto_scroll_parent)

    def _auto_scroll_parent(self) -> None:
        """Periodically scroll parent container during streaming.

        This timer runs continuously to keep the ChatView scrolled
        to the bottom as the streaming widget grows in height.
        """
        if self.streaming and self.parent and hasattr(self.parent, 'scroll_end'):
            self.parent.scroll_end(animate=False)

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
            # Write only the NEW content since last write (append mode)
            new_content = self.full_content[self._last_written_length:]
            if new_content:
                logger.debug(f"Appending {len(new_content)} new chars to RichLog")
                self.write(new_content)  # Use plain text, CSS handles styling
                self._last_written_length = len(self.full_content)
                # Scroll to bottom to follow the streaming content
                self.scroll_end(animate=False)
            self.token_buffer.clear()
            self.last_render_time = current_time

    async def _render_content(self, force: bool = False) -> None:
        """No longer used - render() method is called automatically."""
        pass

    async def finalize_stream(self) -> None:
        """Finalize streaming and render final content.

        Marks streaming as complete, renders any remaining buffered
        tokens, and updates the border title with token count.
        """
        self.streaming = False
        self.token_buffer.clear()
        # Write final content without cursor
        self.clear()
        self.write(self.full_content)
        self.border_title = f"Assistant ({self.token_count} tokens)"

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
