"""LocalModelCard - Card widget for displaying locally available models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Click

    from consoul.sdk.models import ModelInfo

__all__ = ["LocalModelCard"]


class LocalModelCard(Vertical):
    """A card widget for displaying a locally available AI model.

    Displays local model information including name, provider, size,
    model type/quantization, and capabilities.
    """

    class CardClicked(Message):
        """Message sent when a card is clicked."""

        def __init__(self, model_id: str, provider: str) -> None:
            """Initialize CardClicked message.

            Args:
                model_id: ID of the model that was clicked
                provider: Provider name
            """
            super().__init__()
            self.model_id = model_id
            self.provider = provider

    DEFAULT_CSS = """
    LocalModelCard {
        width: 100%;
        height: auto;
        min-height: 5;
        padding: 1;
        margin: 0 1 1 0;
        background: $surface;
        border: round $primary;
    }

    LocalModelCard:hover {
        background: $surface-lighten-1;
        border: round $accent;
    }

    LocalModelCard.selected {
        border: round #4BB543;
    }

    LocalModelCard.selected:hover {
        background: $primary-lighten-1;
    }

    LocalModelCard .model-header {
        width: 100%;
        height: auto;
    }

    LocalModelCard .model-name {
        width: 1fr;
        color: $text;
        text-style: bold;
    }

    LocalModelCard.selected .model-name {
        color: auto;
    }

    LocalModelCard .provider-badge {
        width: auto;
        padding: 0 1;
        color: $text;
        text-align: right;
    }

    LocalModelCard .provider-badge.ollama {
        background: #6366f1;
    }

    LocalModelCard .provider-badge.llamacpp {
        background: #f59e0b;
    }

    LocalModelCard .provider-badge.mlx {
        background: #8b5cf6;
    }

    LocalModelCard .provider-badge.huggingface {
        background: #eab308;
    }

    LocalModelCard .model-description {
        width: 100%;
        color: $text-muted;
        margin-top: 1;
    }

    LocalModelCard.selected .model-description {
        color: auto 70%;
    }

    LocalModelCard .model-metadata {
        width: 100%;
        height: auto;
        margin-top: 1;
    }

    LocalModelCard .metadata-label {
        color: $text-muted;
        width: auto;
    }

    LocalModelCard .metadata-value {
        color: $text;
        width: auto;
        text-style: bold;
    }

    LocalModelCard .capability-badge {
        width: auto;
        padding: 0 1;
        margin-right: 1;
        margin-left: 1;
        background: $success;
        color: $text;
    }

    LocalModelCard .capability-badge.vision {
        background: $warning;
    }

    LocalModelCard .capability-badge.tools {
        background: $accent;
    }

    LocalModelCard .capability-badge.reasoning {
        background: $success;
    }
    """

    # Reactive state
    is_selected: reactive[bool] = reactive(False)

    def __init__(
        self,
        model: ModelInfo,
        is_current: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize LocalModelCard.

        Args:
            model: ModelInfo object for this local model
            is_current: Whether this is the currently active model
            **kwargs: Additional arguments for Vertical
        """
        super().__init__(**kwargs)
        self.model = model
        self.is_selected = is_current
        self.model_id = model.id
        self.provider = model.provider

    def compose(self) -> ComposeResult:
        """Compose the local model card layout."""
        # Header: model name + provider badge
        with Horizontal(classes="model-header"):
            yield Label(self.model.name, classes="model-name")
            yield Label(
                self.provider.upper(),
                classes=f"provider-badge {self.provider}",
            )

        # Description with size/type info
        yield Label(self.model.description, classes="model-description")

        # Metadata row: context window, capabilities
        with Horizontal(classes="model-metadata"):
            # Context window
            if self.model.context_window and self.model.context_window != "?":
                yield Label("Context: ", classes="metadata-label")
                yield Label(self.model.context_window, classes="metadata-value")

            # Vision capability badge
            if self.model.supports_vision:
                yield Label("VISION", classes="capability-badge vision")

            # Tools capability badge
            if self.model.supports_tools:
                yield Label("TOOLS", classes="capability-badge tools")

            # Reasoning capability badge
            if self.model.supports_reasoning:
                yield Label("THINKING", classes="capability-badge reasoning")

    def watch_is_selected(self, is_selected: bool) -> None:
        """React to selection state changes."""
        self.set_class(is_selected, "selected")

    def on_click(self, event: Click) -> None:
        """Handle click events."""
        event.stop()
        self.post_message(self.CardClicked(self.model_id, self.provider))
