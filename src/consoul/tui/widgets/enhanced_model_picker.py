"""EnhancedModelPicker - Modern model selection interface with card-based UI.

This modal provides an enhanced interface for selecting AI models with:
- Tabbed navigation by provider
- Card-based model display
- Live search and capability filtering
- Visual pricing indicators
- Keyboard-friendly navigation
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, TabbedContent, TabPane

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.config.models import Provider
    from consoul.registry.types import ModelEntry

from consoul.registry import list_models
from consoul.tui.widgets.model_card import ModelCard

__all__ = ["EnhancedModelPicker"]


class EnhancedModelPicker(ModalScreen[tuple[str, str] | None]):
    """Enhanced model picker with card-based UI and filtering.

    Features:
    - Provider tabs (OpenAI, Anthropic, Google)
    - Card-based model display
    - Live search filtering
    - Capability filters (vision, tools, reasoning)
    - Visual pricing indicators (green/yellow/red)
    - Keyboard navigation (arrows, enter, escape, ctrl+f)

    Returns:
        Tuple of (provider, model_id) or None if cancelled
    """

    BINDINGS: ClassVar = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+f", "focus_search", "Search", show=True),
    ]

    DEFAULT_CSS = """
    EnhancedModelPicker {
        align: center middle;
    }

    #picker-container {
        width: 140;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #modal-header {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    #modal-title {
        width: 1fr;
        text-align: center;
        text-style: bold;
        color: $text;
    }

    #close-button {
        min-width: 7;
        background: transparent;
        border: none;
        color: $text-muted;
        text-style: bold;
    }

    #close-button:hover {
        color: $error;
        background: transparent;
        text-style: bold;
    }

    #close-button:focus {
        background: transparent;
    }

    EnhancedModelPicker TabbedContent {
        height: 1fr;
    }

    EnhancedModelPicker TabPane {
        padding: 0;
    }

    #search-filter-container {
        height: auto;
        width: 100%;
        margin-bottom: 1;
    }

    #search-filter-container Input {
        width: 3fr;
        margin-right: 1;
    }

    #search-filter-container Select {
        width: 1fr;
        background: $surface;
    }

    #models-container {
        height: 1fr;
    }

    #models-scroll {
        height: 100%;
        background: $panel;
    }
    """

    # Reactive state
    search_query: reactive[str] = reactive("")
    filter_vision: reactive[bool] = reactive(False)
    filter_tools: reactive[bool] = reactive(False)
    filter_reasoning: reactive[bool] = reactive(False)

    def __init__(
        self,
        current_model: str,
        current_provider: "Provider",
        **kwargs: str,
    ) -> None:
        """Initialize the enhanced model picker.

        Args:
            current_model: Currently selected model ID
            current_provider: Currently selected provider
            **kwargs: Additional arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.current_model = current_model
        self.current_provider = current_provider
        self._all_models = list_models(active_only=True)
        self._selected_model_id: str | None = None
        self._selected_provider: str | None = None

    def _group_by_provider(self) -> dict[str, list[ModelEntry]]:
        """Group models by provider.

        Returns:
            Dictionary mapping provider names to model lists
        """
        providers: dict[str, list[ModelEntry]] = defaultdict(list)
        for model in self._all_models:
            provider_name = model.metadata.provider
            providers[provider_name].append(model)

        # Sort models within each provider by release date (newest first)
        for provider in providers:
            providers[provider].sort(key=lambda m: m.metadata.created, reverse=True)

        return providers

    def compose(self) -> ComposeResult:
        """Compose the enhanced picker UI."""
        with Vertical(id="picker-container"):
            # Header with title and close button
            with Horizontal(id="modal-header"):
                yield Label("Select AI Model", id="modal-title")
                yield Button(" ✖ ", id="close-button")

            # Group models by provider
            providers = self._group_by_provider()

            # Tabbed content for providers
            with TabbedContent(initial=self.current_provider.value):
                for provider_name, models in sorted(providers.items()):
                    with TabPane(provider_name.title(), id=provider_name):
                        # Search input and filter dropdown
                        with Horizontal(id="search-filter-container"):
                            yield Input(
                                placeholder="Search models...",
                                id=f"search-{provider_name}",
                            )
                            yield Select(
                                [
                                    ("All Models", "all"),
                                    ("Vision", "vision"),
                                    ("Tools", "tools"),
                                    ("Reasoning", "reasoning"),
                                ],
                                value="all",
                                id=f"filter-{provider_name}",
                            )

                        # Models scroll container
                        with (
                            Vertical(id="models-container"),
                            VerticalScroll(id=f"models-scroll-{provider_name}"),
                        ):
                            # Add model cards
                            for model in models:
                                is_current = model.id == self.current_model
                                card = ModelCard(model, is_current=is_current)
                                card.add_class(f"model-card-{provider_name}")
                                yield card

    def on_mount(self) -> None:
        """Handle mount event."""
        # Pre-select the current model
        for card in self.query(ModelCard):
            if card.model_id == self.current_model:
                card.is_selected = True
                self._selected_model_id = card.model_id
                self._selected_provider = card.provider
                break

        # Focus the search input for the current provider
        search_id = f"search-{self.current_provider.value}"
        try:
            search_input = self.query_one(f"#{search_id}", Input)
            search_input.focus()
        except Exception:
            pass

    def on_model_card_card_clicked(self, message: ModelCard.CardClicked) -> None:
        """Handle model card clicks - select and dismiss immediately."""
        message.stop()

        # Select and dismiss with the clicked model
        self.dismiss((message.provider, message.model_id))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        event.stop()
        self.search_query = event.value

        # Get current provider from active tab
        try:
            tabbed_content = self.query_one(TabbedContent)
            current_provider = tabbed_content.active
        except Exception:
            return

        # Re-apply all filters (search + capability)
        self._apply_capability_filters(current_provider)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "close-button":
            self.dismiss(None)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter dropdown selection changes."""
        if not event.select.id or not event.select.id.startswith("filter-"):
            return

        # Extract provider from select id
        provider = event.select.id.replace("filter-", "")

        # Reset all filters
        self.filter_vision = False
        self.filter_tools = False
        self.filter_reasoning = False

        # Set the selected filter based on dropdown value
        if event.value == "vision":
            self.filter_vision = True
        elif event.value == "tools":
            self.filter_tools = True
        elif event.value == "reasoning":
            self.filter_reasoning = True
        # "all" shows everything (all filters False)

        self._apply_capability_filters(provider)

    def _apply_capability_filters(self, provider: str) -> None:
        """Apply capability filters to cards for the given provider."""
        for card in self.query(ModelCard):
            if not card.has_class(f"model-card-{provider}"):
                continue

            # First check if it matches search query
            query = self.search_query.lower()
            search_match = True
            if query:
                name_match = query in card.model.name.lower()
                desc_match = query in card.model.metadata.description.lower()
                search_match = name_match or desc_match

            # Then check capability filters
            capability_match = True
            if self.filter_vision:
                capability_match = card.model.supports_vision()
            elif self.filter_tools:
                capability_match = card.model.supports_tools()
            elif self.filter_reasoning:
                capability_match = card.model.supports_reasoning()
            # If no filter is active (all False), capability_match stays True

            # Show only if both search and capability match
            card.display = search_match and capability_match

    def action_cancel(self) -> None:
        """Cancel action."""
        self.dismiss(None)

    def action_focus_search(self) -> None:
        """Focus search input."""
        try:
            tabbed_content = self.query_one(TabbedContent)
            current_provider = tabbed_content.active
            search_id = f"search-{current_provider}"
            search_input = self.query_one(f"#{search_id}", Input)
            search_input.focus()
        except Exception:
            pass
