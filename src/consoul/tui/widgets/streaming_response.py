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
from textual.widgets import Static

__all__ = ["StreamingResponse"]

logger = logging.getLogger(__name__)


class StreamingResponse(Static):
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
            **kwargs: Additional arguments passed to Static
        """
        super().__init__(**kwargs)
        self.renderer_mode = renderer
        self.token_buffer: list[str] = []
        self.full_content = ""
        self.last_render_time = 0.0
        self.render_pending = False
        self._markdown_failed = False

    def on_mount(self) -> None:
        """Initialize streaming response widget on mount."""
        self.border_title = "Assistant"
        self.add_class("streaming-response")

    def render(self) -> str | Text:
        """Render the streaming content.

        This method is called by Textual whenever the widget needs to be redrawn.
        """
        logger.debug(f"render() ENTRY: full_content len={len(self.full_content)}, streaming={self.streaming}")

        if not self.full_content:
            logger.debug("render() returning empty string")
            return ""

        display = self.full_content
        if self.streaming:
            display += " ▌"

        logger.debug(f"render() returning Text: len={len(display)}")

        # Return plain text with explicit styling for visibility
        from rich.text import Text as RichText
        result = RichText(display, style="yellow on red")
        logger.debug(f"render() created RichText: {result}")
        return result

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
            logger.debug("Triggering render")
            self.token_buffer.clear()
            self.last_render_time = current_time
            # Force a screen refresh
            self.refresh()
            if self.screen:
                self.screen.refresh()
            logger.debug(f"Refreshed widget and screen")

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
        self.refresh()
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
        self._markdown_failed = False
        self.last_render_time = 0.0
        self.refresh()
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
        # Refresh when streaming state changes
        self.refresh()
