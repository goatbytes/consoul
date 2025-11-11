"""TypingIndicator widget for showing loading state before AI streaming.

This module provides a loading indicator with pulsing dots that appears
between message submission and the first streaming token.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["TypingIndicator"]


class TypingIndicator(Container):
    """Loading indicator with pulsing dots for AI response waiting state.

    Displays an animated "Assistant is typing..." message with pulsing dots
    styled to match assistant message bubbles.

    Attributes:
        dot_count: Number of dots currently displayed (cycles 0-3)
    """

    DEFAULT_CSS = """
    TypingIndicator {
        width: 100%;
        height: auto;
        padding: 1 2;
        margin: 1 0;
        background: transparent;
        border: round $success;
        border-title-color: $success;
        border-title-align: left;
    }

    TypingIndicator .typing-text {
        width: 100%;
        height: auto;
        color: $text-muted;
        text-style: italic;
    }

    TypingIndicator .typing-dots {
        width: auto;
        height: auto;
        color: $success;
        text-style: bold;
    }
    """

    # Reactive state
    dot_count: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Initialize TypingIndicator.

        Args:
            **kwargs: Additional keyword arguments passed to Container
        """
        super().__init__(**kwargs)
        self.border_title = "Assistant"

    def compose(self) -> ComposeResult:
        """Compose typing indicator widgets.

        Yields:
            Static widgets for typing text and animated dots
        """
        yield Static("Thinking", classes="typing-text", id="typing-text")
        yield Static("", classes="typing-dots", id="typing-dots")

    def on_mount(self) -> None:
        """Start pulsing animation on mount."""
        # Update dots every 500ms
        self.set_interval(0.5, self._update_dots)

    def _update_dots(self) -> None:
        """Update pulsing dots animation."""
        # Cycle through 0-3 dots
        self.dot_count = (self.dot_count + 1) % 4

        # Update dots display (use non-breaking space to maintain height)
        dots_widget = self.query_one("#typing-dots", Static)
        dots_text = "." * self.dot_count if self.dot_count > 0 else "\u00a0"
        dots_widget.update(dots_text)
