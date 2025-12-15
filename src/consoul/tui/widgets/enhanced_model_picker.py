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
    from consoul.sdk.models import ModelInfo
    from consoul.sdk.services.model import ModelService

from consoul.registry import list_models
from consoul.tui.widgets.local_model_card import LocalModelCard
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
        current_provider: Provider,
        model_service: ModelService | None = None,
        **kwargs: str,
    ) -> None:
        """Initialize the enhanced model picker.

        Args:
            current_model: Currently selected model ID
            current_provider: Currently selected provider
            model_service: Optional ModelService instance for local model discovery
            **kwargs: Additional arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.current_model = current_model
        self.current_provider = current_provider
        self.model_service = model_service
        self._all_models = list_models(active_only=True)
        self._local_models: list[ModelInfo] = []
        self._selected_model_id: str | None = None
        self._selected_provider: str | None = None

    def _get_model_priority(self, model: ModelInfo) -> tuple[int, int, int, str]:
        """Get sorting priority for a model.

        Priority order:
        1. Provider (ollama -> mlx -> llamacpp -> huggingface)
        2. Model family priority (gpt-oss, granite, qwen, llama, gemma, devstral, mistral)
        3. Popularity on ollama.com (from static data)
        4. Model name

        Returns:
            Tuple for sorting (provider_priority, family_priority, popularity, name)
        """
        # Provider priority
        provider_order = {"ollama": 0, "mlx": 1, "llamacpp": 2, "huggingface": 3}
        provider_priority = provider_order.get(model.provider, 99)

        # Model family priority
        model_name_lower = model.name.lower()
        family_priorities = {
            "gpt-oss": 0,
            "granite": 1,
            "qwen": 2,
            "llama": 3,
            "gemma": 4,
            "devstral": 5,
            "mistral": 6,
        }

        family_priority = 99  # Default for unknown families
        for family, priority in family_priorities.items():
            if family in model_name_lower:
                family_priority = priority
                break

        # Popularity from ollama.com static data
        popularity = 999999  # Default for models not in static data
        if model.provider == "ollama":
            # Try to get popularity from static data
            try:
                from consoul.ai.ollama_library import load_static_models

                static_models = load_static_models()
                # Extract base model name (remove tag)
                base_name = (
                    model.name.split(":")[0] if ":" in model.name else model.name
                )

                # Find matching model in static data
                for static_model in static_models:
                    if static_model.name == base_name:
                        # Parse num_pulls (e.g., "100M+", "1B+", "500K+")
                        pulls_str = static_model.num_pulls
                        if pulls_str and pulls_str != "Pulls":
                            # Convert to number for sorting
                            # B (billion) = 1000000000, M (million) = 1000000, K (thousand) = 1000
                            multipliers = {
                                "B": 1_000_000_000,
                                "M": 1_000_000,
                                "K": 1_000,
                            }
                            for suffix, multiplier in multipliers.items():
                                if suffix in pulls_str.upper():
                                    try:
                                        num = float(
                                            pulls_str.upper()
                                            .replace(suffix, "")
                                            .replace("+", "")
                                            .strip()
                                        )
                                        popularity = -int(
                                            num * multiplier
                                        )  # Negative for descending sort
                                        break
                                    except (ValueError, AttributeError):
                                        pass
                        break
            except Exception:
                pass  # Ignore errors, use default popularity

        return (provider_priority, family_priority, popularity, model_name_lower)

    def _discover_local_models(self) -> list[ModelInfo]:
        """Discover locally available models.

        Returns:
            List of ModelInfo for all local models, sorted by:
            1. Provider (ollama first, then MLX, llamacpp, huggingface)
            2. Model family priority (gpt-oss, granite, qwen, llama, gemma, devstral, mistral)
            3. Popularity on ollama.com
            4. Model name alphabetically
        """
        from contextlib import suppress

        if not self.model_service:
            return []

        local_models: list[ModelInfo] = []

        with suppress(Exception):
            # Discover Ollama models (fast - uses cached context sizes)
            # Context sizes are loaded from cache (~/.consoul/cache/ollama_context_sizes.json)
            # Background thread refreshes cache for next time (no UI blocking)
            local_models.extend(
                self.model_service.list_ollama_models(
                    include_context=False,
                    use_context_cache=True,
                )
            )

            # Trigger background refresh of context sizes for next time
            # This runs in a separate thread and won't block the UI
            self.model_service.refresh_ollama_context_in_background()

        with suppress(Exception):
            # Discover GGUF models
            local_models.extend(self.model_service.list_gguf_models())

        with suppress(Exception):
            # Discover MLX models
            local_models.extend(self.model_service.list_mlx_models())

        with suppress(Exception):
            # Discover HuggingFace models
            local_models.extend(self.model_service.list_huggingface_models())

        # Sort by custom priority (provider -> family -> popularity -> name)
        local_models.sort(key=self._get_model_priority)

        return local_models

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

            # Discover local models
            self._local_models = self._discover_local_models()

            # Group cloud models by provider
            providers = self._group_by_provider()

            # Determine initial tab
            initial_tab = self.current_provider.value
            # If current provider is local, show local tab
            if self.current_provider.value in (
                "ollama",
                "llamacpp",
                "mlx",
                "huggingface",
            ):
                initial_tab = "local"

            # Tabbed content for providers
            with TabbedContent(initial=initial_tab):
                # Local models tab (first)
                if self._local_models or self.model_service:
                    with TabPane("Local", id="local"):
                        # Search input and filter dropdown
                        with Horizontal(id="search-filter-container"):
                            yield Input(
                                placeholder="Search local models...",
                                id="search-local",
                            )
                            yield Select(
                                [
                                    ("All Local", "all"),
                                    ("Ollama", "ollama"),
                                    ("GGUF/LlamaCpp", "llamacpp"),
                                    ("MLX", "mlx"),
                                    ("HuggingFace", "huggingface"),
                                    ("Vision", "vision"),
                                ],
                                value="all",
                                id="filter-local",
                            )

                        # Models scroll container
                        with (
                            Vertical(id="models-container"),
                            VerticalScroll(id="models-scroll-local"),
                        ):
                            if self._local_models:
                                # Add local model cards
                                for model in self._local_models:
                                    is_current = model.id == self.current_model
                                    card = LocalModelCard(model, is_current=is_current)
                                    card.add_class("model-card-local")
                                    card.add_class(f"local-provider-{model.provider}")
                                    yield card
                            else:
                                # No local models found
                                yield Label(
                                    "No local models found.\n\n"
                                    "Install Ollama, GGUF, MLX, or HuggingFace models to see them here.",
                                    classes="model-description",
                                )

                # Cloud provider tabs
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
                            model_entry: ModelEntry
                            for model_entry in models:
                                is_current = model_entry.id == self.current_model
                                cloud_model_card: ModelCard = ModelCard(
                                    model_entry, is_current=is_current
                                )
                                cloud_model_card.add_class(
                                    f"model-card-{provider_name}"
                                )
                                yield cloud_model_card

    def on_mount(self) -> None:
        """Handle mount event."""
        # Pre-select the current model (check both cloud and local cards)
        cloud_card: ModelCard
        for cloud_card in self.query(ModelCard):
            if cloud_card.model_id == self.current_model:
                cloud_card.is_selected = True
                self._selected_model_id = cloud_card.model_id
                self._selected_provider = cloud_card.provider
                break

        local_card: LocalModelCard
        for local_card in self.query(LocalModelCard):
            if local_card.model_id == self.current_model:
                local_card.is_selected = True
                self._selected_model_id = local_card.model_id
                self._selected_provider = local_card.provider
                break

        # Focus the search input for the current provider
        search_id = f"search-{self.current_provider.value}"
        # For local providers, use local search
        if self.current_provider.value in ("ollama", "llamacpp", "mlx", "huggingface"):
            search_id = "search-local"

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

    def on_local_model_card_card_clicked(
        self, message: LocalModelCard.CardClicked
    ) -> None:
        """Handle local model card clicks - select and dismiss immediately."""
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
        # Handle local tab separately
        if provider == "local":
            self._apply_local_filters()
            return

        # Handle cloud provider tabs
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

    def _apply_local_filters(self) -> None:
        """Apply filters to local model cards."""
        query = self.search_query.lower()

        for card in self.query(LocalModelCard):
            if not card.has_class("model-card-local"):
                continue

            # First check if it matches search query
            search_match = True
            if query:
                name_match = query in card.model.name.lower()
                desc_match = query in card.model.description.lower()
                search_match = name_match or desc_match

            # Then check provider/capability filters
            filter_match = True
            if self.filter_vision:
                # Vision filter
                filter_match = card.model.supports_vision
            elif self.filter_tools:
                # Tools filter (not applicable to local, show all)
                filter_match = True
            elif self.filter_reasoning:
                # Reasoning filter (not applicable to local, show all)
                filter_match = True
            else:
                # Check for provider-specific filter by looking at select value
                # This will be "ollama", "llamacpp", "mlx", "huggingface", or "all"
                try:
                    select = self.query_one("#filter-local", Select)
                    filter_value = str(select.value)
                    if filter_value in ("ollama", "llamacpp", "mlx", "huggingface"):
                        filter_match = card.model.provider == filter_value
                except Exception:
                    pass

            # Show only if both search and filter match
            card.display = search_match and filter_match

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
