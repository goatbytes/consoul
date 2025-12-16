"""OllamaLibraryModal - Beautiful modal for browsing and discovering Ollama models."""

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, LoadingIndicator, Static

from consoul.ai.ollama_library import OllamaLibraryModel, fetch_library_models

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Click

__all__ = ["OllamaLibraryModal"]


class ModelCard(Container):
    """A beautiful card widget displaying a single Ollama model."""

    DEFAULT_CSS = """
    ModelCard {
        width: 100%;
        height: auto;
        min-height: 8;
        border: solid $primary-lighten-2;
        background: $panel;
        padding: 1 2;
        margin: 0 0 1 0;
    }

    ModelCard:hover {
        border: solid $accent;
        background: $panel-lighten-1;
    }

    ModelCard.selected {
        border: thick $accent;
        background: $panel-lighten-1;
    }

    ModelCard .model-name {
        width: 100%;
        text-style: bold;
        color: $accent;
        margin: 0 0 0 0;
    }

    ModelCard .model-description {
        width: 100%;
        color: $text;
        margin: 0 0 1 0;
    }

    ModelCard .model-metadata {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin: 0 0 0 0;
    }

    ModelCard .metadata-item {
        width: auto;
        color: $text-muted;
        margin-right: 2;
    }

    ModelCard .metadata-label {
        color: $primary;
        text-style: bold;
    }
    """

    def __init__(self, model: OllamaLibraryModel, **kwargs: Any) -> None:
        """Initialize the model card.

        Args:
            model: The Ollama model to display
            **kwargs: Additional arguments for Container
        """
        super().__init__(**kwargs)
        self.model = model
        self.can_focus = True

    def compose(self) -> ComposeResult:
        """Compose the model card layout."""
        # Model name
        yield Label(self.model.name, classes="model-name")

        # Description
        description = self.model.description
        if len(description) > 150:
            description = description[:147] + "..."
        yield Label(description, classes="model-description")

        # Metadata row
        with Horizontal(classes="model-metadata"):
            if self.model.num_pulls:
                yield Static(
                    f"[bold]↓[/bold] {self.model.num_pulls}",
                    classes="metadata-item",
                )
            if self.model.num_tags:
                yield Static(
                    f"[bold]🏷[/bold] {self.model.num_tags}",
                    classes="metadata-item",
                )
            if self.model.updated:
                yield Static(
                    f"[bold]📅[/bold] {self.model.updated}",
                    classes="metadata-item",
                )

    async def on_click(self, event: Click) -> None:
        """Handle click on the model card."""
        event.stop()
        # Open in browser
        webbrowser.open(self.model.url)
        self.app.notify(f"Opening {self.model.name} in browser...", timeout=3)


class OllamaLibraryModal(ModalScreen[None]):
    """Beautiful modal for browsing and discovering Ollama models from ollama.com.

    Features:
    - Card-based layout with model details
    - Search/filter functionality
    - Click to open model page in browser
    - Cached results (24-hour expiry)
    """

    DEFAULT_CSS = """
    OllamaLibraryModal {
        align: center middle;
    }

    OllamaLibraryModal > Vertical {
        width: 90;
        height: 90%;
        max-width: 120;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    OllamaLibraryModal .modal-header {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin: 0 0 1 0;
    }

    OllamaLibraryModal .modal-title {
        width: 1fr;
        content-align: left middle;
        text-style: bold;
        color: $text;
    }

    OllamaLibraryModal .modal-subtitle {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        text-style: italic;
        margin: 0 0 1 0;
    }

    OllamaLibraryModal #search-input {
        width: 100%;
        margin: 0 0 1 0;
    }

    OllamaLibraryModal #models-container {
        width: 100%;
        height: 1fr;
        border: solid $primary-lighten-2;
    }

    OllamaLibraryModal #loading-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    OllamaLibraryModal #empty-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    OllamaLibraryModal .empty-message {
        color: $text-muted;
        text-style: italic;
    }

    OllamaLibraryModal .button-container {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin: 1 0 0 0;
    }

    OllamaLibraryModal Button {
        min-width: 16;
        margin: 0 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Close", show=False),
        Binding("ctrl+r", "refresh", "Refresh", show=True),
        Binding("/", "focus_search", "Search", show=True),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the Ollama Library modal."""
        super().__init__(**kwargs)
        self.models: list[OllamaLibraryModel] = []
        self.filtered_models: list[OllamaLibraryModel] = []
        self.loading = True

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical():
            # Header
            with Horizontal(classes="modal-header"):
                yield Label("🦙 Ollama Model Library", classes="modal-title")

            yield Label(
                "Browse and discover models from ollama.com · Click to open in browser",
                classes="modal-subtitle",
            )

            # Search input
            yield Input(
                placeholder="Search models...",
                id="search-input",
            )

            # Models container
            with (
                VerticalScroll(id="models-container"),
                Vertical(id="loading-container"),
            ):
                yield LoadingIndicator()
                yield Label("Loading models from ollama.com...")

            # Buttons
            with Horizontal(classes="button-container"):
                yield Button("Refresh", variant="default", id="refresh-btn")
                yield Button("Close", variant="primary", id="close-btn")

    async def on_mount(self) -> None:
        """Load models when the modal is mounted."""
        await self._load_models()

    async def _load_models(self, force_refresh: bool = False) -> None:
        """Load models from ollama.com.

        Args:
            force_refresh: Force refresh even if cache is valid
        """
        self.loading = True

        try:
            # Fetch models (uses 24-hour cache) - run in thread pool to avoid blocking
            import asyncio

            self.models = await asyncio.to_thread(
                fetch_library_models,
                namespace="library",
                category=None,
                force_refresh=force_refresh,
            )

            self.filtered_models = self.models.copy()
            self.loading = False

            # Update UI
            await self._update_models_display()

        except Exception as e:
            self.loading = False
            self.app.notify(
                f"Failed to load Ollama Library: {e!s}",
                severity="error",
                timeout=10,
            )

            # Show error message
            container = self.query_one("#models-container", VerticalScroll)
            await container.remove_children()
            await container.mount(
                Vertical(
                    Label("Failed to load models", classes="empty-message"),
                    Label(str(e), classes="empty-message"),
                    id="empty-container",
                )
            )

    async def _update_models_display(self) -> None:
        """Update the models display with current filtered models."""
        container = self.query_one("#models-container", VerticalScroll)
        await container.remove_children()

        if not self.filtered_models:
            # Show empty state
            await container.mount(
                Vertical(
                    Label("No models found", classes="empty-message"),
                    Label(
                        "Try adjusting your search query",
                        classes="empty-message",
                    ),
                    id="empty-container",
                )
            )
        else:
            # Show model cards
            for model in self.filtered_models:
                await container.mount(ModelCard(model))

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id != "search-input":
            return

        search_query = event.value.lower().strip()

        if not search_query:
            self.filtered_models = self.models.copy()
        else:
            self.filtered_models = [
                model
                for model in self.models
                if search_query in model.name.lower()
                or search_query in model.description.lower()
                or any(search_query in tag.lower() for tag in model.tags)
            ]

        await self._update_models_display()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-btn":
            self.dismiss(None)
        elif event.button.id == "refresh-btn":
            await self._load_models(force_refresh=True)
            self.app.notify("Refreshing models...", timeout=3)

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    async def action_refresh(self) -> None:
        """Refresh models from ollama.com."""
        await self._load_models(force_refresh=True)
        self.app.notify("Refreshing models...", timeout=3)

    def action_focus_search(self) -> None:
        """Focus the search input."""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()
