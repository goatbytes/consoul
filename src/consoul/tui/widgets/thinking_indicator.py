"""ThinkingIndicator widget for showing AI reasoning/chain-of-thought state.

This module provides a visual indicator that appears when the AI is streaming
thinking/reasoning content (e.g., content within <think> tags). It shows a pulsing
animation to indicate the model is in "thinking mode" before providing the answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["ThinkingIndicator"]


class ThinkingIndicator(Container):
    """Visual indicator for AI thinking/reasoning state during streaming.

    Displays an animated "🧠 Thinking..." message with pulsing dots to show
    that the AI is currently outputting chain-of-thought reasoning before
    providing the final answer.

    Attributes:
        dot_count: Number of dots currently displayed (cycles 0-3)
    """

    DEFAULT_CSS = """
    ThinkingIndicator {
        width: 100%;
        height: auto;
        padding: 1 2;
        margin: 1 0;
        background: $surface-darken-1;
        border: dashed $primary;
        border-title-color: $primary;
        border-title-align: left;
    }

    ThinkingIndicator .thinking-text {
        width: 100%;
        height: auto;
        color: $text-muted;
        text-style: italic;
    }

    ThinkingIndicator .thinking-dots {
        width: auto;
        height: auto;
        color: $primary;
        text-style: bold;
    }
    """

    # Reactive state
    dot_count: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Initialize ThinkingIndicator.

        Args:
            **kwargs: Additional keyword arguments passed to Container
        """
        super().__init__(**kwargs)
        self.border_title = "🧠 Thinking"

    def compose(self) -> ComposeResult:
        """Compose thinking indicator widgets.

        Yields:
            Static widgets for thinking text and animated dots
        """
        yield Static("Reasoning", classes="thinking-text", id="thinking-text")
        yield Static("", classes="thinking-dots", id="thinking-dots")

    def on_mount(self) -> None:
        """Start pulsing animation on mount."""
        # Update dots every 400ms (slightly faster than typing indicator)
        self.set_interval(0.4, self._update_dots)

    def _update_dots(self) -> None:
        """Update pulsing dots animation."""
        # Cycle through 0-3 dots
        self.dot_count = (self.dot_count + 1) % 4

        # Update dots display (use non-breaking space to maintain height)
        dots_widget = self.query_one("#thinking-dots", Static)
        dots_text = "." * self.dot_count if self.dot_count > 0 else "\u00a0"
        dots_widget.update(dots_text)
