"""ModelSelectorModal - Modal for selecting AI models within a provider."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.config.models import Provider

__all__ = ["ModelSelectorModal"]

log = logging.getLogger(__name__)


# Model information database (name -> metadata)
# This is a simplified version - in production, you might fetch this from provider APIs
MODEL_INFO = {
    # OpenAI models
    "gpt-4": {
        "provider": "openai",
        "context": "8K",
        "cost": "expensive",
        "description": "Most capable GPT-4 model",
    },
    "gpt-4-turbo": {
        "provider": "openai",
        "context": "128K",
        "cost": "expensive",
        "description": "Latest GPT-4 with larger context",
    },
    "gpt-4o": {
        "provider": "openai",
        "context": "128K",
        "cost": "moderate",
        "description": "Optimized GPT-4 model",
    },
    "gpt-3.5-turbo": {
        "provider": "openai",
        "context": "16K",
        "cost": "cheap",
        "description": "Fast and affordable",
    },
    # Anthropic models
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
    "gemini-pro": {
        "provider": "google",
        "context": "32K",
        "cost": "moderate",
        "description": "Google's capable model",
    },
    "gemini-1.5-pro": {
        "provider": "google",
        "context": "2M",
        "cost": "expensive",
        "description": "Huge context window",
    },
    # Ollama models are dynamic and would be fetched from local instance
    # For now, we'll show common ones
    "llama3": {
        "provider": "ollama",
        "context": "8K",
        "cost": "free",
        "description": "Meta's Llama 3 model",
    },
    "mistral": {
        "provider": "ollama",
        "context": "8K",
        "cost": "free",
        "description": "Mistral AI model",
    },
    "codellama": {
        "provider": "ollama",
        "context": "16K",
        "cost": "free",
        "description": "Code-specialized Llama",
    },
}


class ModelSelectorModal(ModalScreen[str | None]):
    """Modal for selecting a model within the current provider.

    Features:
    - DataTable showing available models with current one highlighted
    - Filtered to show only models for current provider
    - Live search/filter by model name
    - Enter key to select, Escape to cancel
    - Returns selected model name or None (cancel)
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "select", "Select", show=False),
    ]

    DEFAULT_CSS = """
    ModelSelectorModal {
        align: center middle;
    }

    ModelSelectorModal #modal-wrapper {
        width: 100;
        height: 70%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    ModelSelectorModal .modal-header {
        width: 100%;
        height: auto;
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    ModelSelectorModal #search-input {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    ModelSelectorModal #models-table {
        width: 100%;
        height: 1fr;
        background: $surface;
    }

    ModelSelectorModal .info-label {
        width: 100%;
        height: auto;
        color: $text-muted;
        margin: 1 0;
        text-align: center;
    }

    ModelSelectorModal #button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    ModelSelectorModal Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        current_model: str,
        provider: Provider,
        **kwargs: Any,
    ) -> None:
        """Initialize the modal.

        Args:
            current_model: Name of currently active model
            provider: Provider to filter models for
        """
        super().__init__(**kwargs)
        self.current_model = current_model
        self.provider = provider
        self._table: DataTable[Any] | None = None
        self._model_map: dict[str, dict[str, str]] = {}  # row_key -> model metadata
        log.info(
            f"ModelSelectorModal: Initialized with current_model={current_model}, provider={provider}"
        )

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical(id="modal-wrapper"):
            # Header
            provider_title = str(self.provider.value).title()
            yield Label(f"Select {provider_title} Model", classes="modal-header")

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
        log.info("ModelSelectorModal: on_mount called, populating models")

        # Initialize table
        self._table = self.query_one("#models-table", DataTable)
        self._table.add_column("Model")
        self._table.add_column("Context")
        self._table.add_column("Cost")
        self._table.add_column("Description")
        self._table.cursor_type = "row"
        self._table.focus()

        # Populate table
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

        # Filter models by provider
        provider_value = self.provider.value
        provider_models = {
            name: info
            for name, info in MODEL_INFO.items()
            if info["provider"] == provider_value
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

        # If current model is not in the database, add it
        if self.current_model not in provider_models:
            provider_models[self.current_model] = {
                "provider": provider_value,
                "context": "?",
                "cost": "?",
                "description": "Custom model",
            }

        # Add rows, sorting by name
        for name in sorted(provider_models.keys()):
            info = provider_models[name]
            row_key = name

            self._model_map[row_key] = info

            # Format columns
            is_current = name == self.current_model
            model_col = f"✓ {name}" if is_current else f"  {name}"
            context_col = info["context"]
            cost_col = info["cost"]
            description_col = (
                info["description"][:30] + "..."
                if len(info["description"]) > 30
                else info["description"]
            )

            self._table.add_row(
                model_col, context_col, cost_col, description_col, key=row_key
            )

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
            f"ModelSelectorModal: Populated table with {len(provider_models)} models"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self._populate_table(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key)."""
        if event.row_key:
            selected_model = str(event.row_key.value)
            log.info(f"ModelSelectorModal: Selected model '{selected_model}'")
            self.dismiss(selected_model)

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
            log.info(f"ModelSelectorModal: Selected model '{selected_model}'")
            self.dismiss(selected_model)

    def action_cancel(self) -> None:
        """Handle cancel action (Escape key)."""
        log.info("ModelSelectorModal: Cancel action")
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "select-btn":
            self.action_select()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
