"""StreamingResponse widget for displaying real-time AI output.

This module provides a widget that handles streaming AI tokens with buffering,
debounced markdown rendering, and fallback strategies to prevent UI freezes.
"""

from __future__ import annotations

import time
from typing import Any, Literal

from rich.markdown import Markdown
from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

__all__ = ["StreamingResponse"]


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

        if buffer_size >= self.BUFFER_SIZE or time_since_render >= self.DEBOUNCE_MS:
            await self._render_content()

    async def _render_content(self, force: bool = False) -> None:
        """Render buffered content based on renderer mode.

        Attempts markdown rendering first, falls back to plain text
        if markdown fails or is too slow.

        Args:
            force: If True, render even when buffer is empty (used during finalization)
        """
        # Skip early return only if we have tokens OR we're forcing a final render
        if not self.token_buffer and not force:
            return

        self.last_render_time = time.time() * 1000
        self.token_buffer.clear()

        # Add streaming cursor
        display_content = self.full_content
        if self.streaming:
            display_content += " ▌"

        # Render based on mode
        if self.renderer_mode == "markdown" and not self._markdown_failed:
            try:
                md = Markdown(self.full_content)
                if self.streaming:
                    # Append cursor for streaming indicator
                    from rich.console import Group

                    cursor = Text(" ▌", style="bold blink")
                    self.update(Group(md, cursor))
                else:
                    self.update(md)
            except Exception:
                # Fallback to plain text if markdown fails
                self._markdown_failed = True
                self.update(display_content)
        elif self.renderer_mode == "hybrid":
            # Use plain text during streaming, markdown on completion
            if self.streaming:
                self.update(display_content)
            else:
                try:
                    md = Markdown(self.full_content)
                    self.update(md)
                except Exception:
                    self.update(self.full_content)
        else:
            # Plain text mode (richlog)
            self.update(display_content)

    async def finalize_stream(self) -> None:
        """Finalize streaming and render final content.

        Marks streaming as complete, renders any remaining buffered
        tokens, and updates the border title with token count.
        """
        self.streaming = False
        await self._render_content(force=True)
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
        self.update("")
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
