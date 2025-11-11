"""ModelPickerModal - Modal for selecting AI models and providers.

This modal provides a unified interface for switching between AI providers
(OpenAI, Anthropic, Google, Ollama) and selecting specific models within each provider.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Click

    from consoul.config.models import Provider

__all__ = ["ModelPickerModal"]

log = logging.getLogger(__name__)


# Model information database (name -> metadata)
# Updated with latest models as of January 2025
MODEL_INFO = {
    # OpenAI models
    "gpt-4o": {
        "provider": "openai",
        "context": "128K",
        "cost": "moderate",
        "description": "Optimized GPT-4 model with vision",
    },
    "gpt-4-turbo": {
        "provider": "openai",
        "context": "128K",
        "cost": "expensive",
        "description": "Latest GPT-4 with larger context",
    },
    "gpt-4": {
        "provider": "openai",
        "context": "8K",
        "cost": "expensive",
        "description": "Original GPT-4 model",
    },
    "gpt-3.5-turbo": {
        "provider": "openai",
        "context": "16K",
        "cost": "cheap",
        "description": "Fast and affordable",
    },
    # Anthropic models
    "claude-3-5-sonnet-20241022": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "moderate",
        "description": "Latest Claude 3.5 Sonnet",
    },
    "claude-3-opus-20240229": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "expensive",
        "description": "Most capable Claude model",
    },
    "claude-3-sonnet-20240229": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "moderate",
        "description": "Balanced Claude model",
    },
    "claude-3-haiku-20240307": {
        "provider": "anthropic",
        "context": "200K",
        "cost": "cheap",
        "description": "Fast Claude model",
    },
    # Google models
    "gemini-1.5-pro": {
        "provider": "google",
        "context": "2M",
        "cost": "expensive",
        "description": "Huge context window",
    },
    "gemini-pro": {
        "provider": "google",
        "context": "32K",
        "cost": "moderate",
        "description": "Google's capable model",
    },
    # Note: Ollama models are fetched dynamically from local service
}


class ModelPickerModal(ModalScreen[tuple[str, str] | None]):
    """Modal for selecting AI provider and model.

    Features:
    - Provider tabs (OpenAI, Anthropic, Google, Ollama)
    - DataTable showing models for selected provider
    - Live search/filter by model name
    - Shows model metadata (context window, cost, rating)
    - Enter key to select, Escape to cancel
    - Returns tuple[provider, model_name] or None (cancel)
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "select", "Select", show=False),
    ]

    DEFAULT_CSS = """
    ModelPickerModal {
        align: center middle;
    }

    ModelPickerModal #modal-wrapper {
        width: 80;
        height: 75%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    ModelPickerModal .modal-header {
        width: 100%;
        height: auto;
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    ModelPickerModal #provider-tabs {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
        margin: 0 0 1 0;
    }

    ModelPickerModal .provider-tab {
        margin: 0 1;
        padding: 0 2;
        background: transparent;
        color: $text-muted;
    }

    ModelPickerModal .provider-tab:hover {
        background: $primary-lighten-1;
        color: $text;
        text-style: bold;
    }

    ModelPickerModal .provider-tab.-active {
        background: $primary;
        color: $accent;
        text-style: bold;
    }

    ModelPickerModal #search-input {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    ModelPickerModal #models-table {
        width: 100%;
        height: 1fr;
        background: $surface;
    }

    ModelPickerModal .info-label {
        width: 100%;
        height: auto;
        color: $text-muted;
        margin: 1 0;
        text-align: center;
    }

    ModelPickerModal #button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    ModelPickerModal Button {
        margin: 0 1;
    }
    """

    # Reactive properties
    active_provider: reactive[str] = reactive("openai")

    def __init__(
        self,
        current_model: str,
        current_provider: Provider,
        **kwargs: Any,
    ) -> None:
        """Initialize the modal.

        Args:
            current_model: Name of currently active model
            current_provider: Currently active provider
        """
        # Initialize attributes before super().__init__ to avoid watcher issues
        self._table: DataTable[Any] | None = None
        self._model_map: dict[str, dict[str, str]] = {}  # row_key -> model metadata

        # Check if Ollama is available
        from consoul.ai.providers import is_ollama_running

        self._ollama_available = is_ollama_running()

        super().__init__(**kwargs)
        self.current_model = current_model
        self.current_provider = current_provider
        self.active_provider = current_provider.value
        log.info(
            f"ModelPickerModal: Initialized with current_model={current_model}, "
            f"current_provider={current_provider}, ollama_available={self._ollama_available}"
        )

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical(id="modal-wrapper"):
            # Header
            yield Label("Select AI Model & Provider", classes="modal-header")

            # Provider tabs (conditionally include Ollama)
            with Horizontal(id="provider-tabs"):
                providers = ["openai", "anthropic", "google"]
                if self._ollama_available:
                    providers.append("ollama")

                for provider in providers:
                    tab_classes = "provider-tab"
                    if provider == self.active_provider:
                        tab_classes += " -active"
                    tab_label = Label(
                        provider.title(),
                        classes=tab_classes,
                        id=f"tab-{provider}",
                    )
                    tab_label.can_focus = True
                    yield tab_label

            # Search/filter input
            yield Input(
                placeholder="Search models by name...",
                id="search-input",
            )

            # DataTable for models
            yield DataTable(id="models-table", zebra_stripes=True, cursor_type="row")

            # Info label
            yield Label("Enter: select · Escape: cancel", classes="info-label")

            # Action buttons
            with Horizontal(id="button-row"):
                yield Button("Select", variant="primary", id="select-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    async def on_mount(self) -> None:
        """Load models and populate table when mounted."""
        log.info("ModelPickerModal: on_mount called, populating models")

        # Initialize table
        self._table = self.query_one("#models-table", DataTable)
        self._table.add_column("Model", width=35)
        self._table.add_column("Context", width=12)
        self._table.add_column("Cost", width=12)
        self._table.cursor_type = "row"
        self._table.focus()

        # Populate table
        self._populate_table()

    def watch_active_provider(self, provider: str) -> None:
        """React to provider tab changes."""
        # Update tab styling
        for tab_id in ["tab-openai", "tab-anthropic", "tab-google", "tab-ollama"]:
            try:
                tab = self.query_one(f"#{tab_id}", Label)
                if tab_id == f"tab-{provider}":
                    tab.add_class("-active")
                else:
                    tab.remove_class("-active")
            except Exception:
                pass

        # Refresh model table
        self._populate_table()

    def _populate_table(self, search_query: str = "") -> None:
        """Populate or refresh the table with models.

        Args:
            search_query: Optional search query to filter models
        """
        if not self._table:
            return

        # Clear existing rows
        self._table.clear()
        self._model_map.clear()

        # Filter models by active provider
        provider_value = self.active_provider
        provider_models = {
            name: info
            for name, info in MODEL_INFO.items()
            if info["provider"] == provider_value
        }

        # For Ollama, fetch dynamic models from the service
        if provider_value == "ollama":
            from consoul.ai.providers import get_ollama_models, is_ollama_running

            if is_ollama_running():
                # Fetch models with context length info
                ollama_models = get_ollama_models(include_context=True)
                for model_info in ollama_models:
                    model_name = model_info.get("name", "")
                    if model_name and model_name not in provider_models:
                        # Format context length
                        context_length = model_info.get("context_length")
                        if context_length:
                            # Convert to human-readable format (e.g., 262144 -> 256K)
                            if context_length >= 1_000_000:
                                context_str = f"{context_length // 1_000_000}M"
                            elif context_length >= 1_000:
                                context_str = f"{context_length // 1_000}K"
                            else:
                                context_str = str(context_length)
                        else:
                            context_str = "?"

                        # Add dynamic Ollama model
                        provider_models[model_name] = {
                            "provider": "ollama",
                            "context": context_str,
                            "cost": "free",
                            "description": "Local Ollama model",
                        }

        # Apply search filter if provided
        if search_query:
            query_lower = search_query.lower()
            provider_models = {
                name: info
                for name, info in provider_models.items()
                if query_lower in name.lower()
                or query_lower in info["description"].lower()
            }

        # If current model is not in the database and matches current provider, add it
        current_provider_value = self.current_provider.value
        if (
            self.current_model not in provider_models
            and provider_value == current_provider_value
        ):
            provider_models[self.current_model] = {
                "provider": provider_value,
                "context": "?",
                "cost": "?",
                "rating": "?",
                "description": "Custom model",
            }

        # Add rows, sorting by name
        for name in sorted(provider_models.keys()):
            info = provider_models[name]
            row_key = name

            self._model_map[row_key] = info

            # Format columns
            is_current = (
                name == self.current_model and provider_value == current_provider_value
            )
            model_col = f"✓ {name}" if is_current else f"  {name}"
            context_col = info["context"]
            cost_col = info["cost"].title()

            self._table.add_row(model_col, context_col, cost_col, key=row_key)

            # Highlight current model row
            if is_current:
                # Move cursor to current model
                try:
                    row_keys_list = list(self._table.rows.keys())
                    row_index = next(
                        (
                            i
                            for i, key in enumerate(row_keys_list)
                            if str(key) == row_key
                        ),
                        None,
                    )
                    if row_index is not None:
                        self._table.move_cursor(row=row_index)
                except (ValueError, Exception):
                    pass

        log.debug(
            f"ModelPickerModal: Populated table with {len(provider_models)} models "
            f"for provider '{provider_value}'"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self._populate_table(event.value)

    async def on_click(self, event: Click) -> None:
        """Handle click events on provider tabs."""
        target_id = (
            event.control.id
            if hasattr(event, "control") and hasattr(event.control, "id")
            else None
        )

        # Provider tab clicks
        if target_id and target_id.startswith("tab-"):
            provider = target_id.replace("tab-", "")
            if provider in ["openai", "anthropic", "google", "ollama"]:
                self.active_provider = provider
                log.info(f"ModelPickerModal: Switched to provider '{provider}'")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key or double-click)."""
        if event.row_key:
            selected_model = str(event.row_key.value)
            log.info(
                f"ModelPickerModal: Selected provider='{self.active_provider}', "
                f"model='{selected_model}'"
            )
            self.dismiss((self.active_provider, selected_model))

    def action_select(self) -> None:
        """Handle select action (Enter key)."""
        if not self._table:
            return

        cursor_row = self._table.cursor_row
        if cursor_row is None:
            return

        # Get row key from cursor position
        row_keys = list(self._table.rows.keys())
        if 0 <= cursor_row < len(row_keys):
            row_key = row_keys[cursor_row]
            selected_model = str(row_key)
            log.info(
                f"ModelPickerModal: Selected provider='{self.active_provider}', "
                f"model='{selected_model}'"
            )
            self.dismiss((self.active_provider, selected_model))

    def action_cancel(self) -> None:
        """Handle cancel action (Escape key)."""
        log.info("ModelPickerModal: Cancel action")
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "select-btn":
            self.action_select()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
