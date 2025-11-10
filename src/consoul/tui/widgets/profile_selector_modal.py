"""ProfileSelectorModal - Modal for selecting AI configuration profiles."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.config.models import ProfileConfig

__all__ = ["ProfileSelectorModal"]

log = logging.getLogger(__name__)


class ProfileSelectorModal(ModalScreen[str | None]):
    """Modal for selecting a configuration profile.

    Features:
    - DataTable showing available profiles with current one highlighted
    - Live search/filter by profile name or description
    - Enter key to select, Escape to cancel
    - Returns selected profile name or None (cancel)
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "select", "Select", show=False),
    ]

    DEFAULT_CSS = """
    ProfileSelectorModal {
        align: center middle;
    }

    ProfileSelectorModal #modal-wrapper {
        width: 100;
        height: 70%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    ProfileSelectorModal .modal-header {
        width: 100%;
        height: auto;
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    ProfileSelectorModal #search-input {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    ProfileSelectorModal #profiles-table {
        width: 100%;
        height: 1fr;
        background: $surface;
    }

    ProfileSelectorModal .info-label {
        width: 100%;
        height: auto;
        color: $text-muted;
        margin: 1 0;
        text-align: center;
    }

    ProfileSelectorModal #button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    ProfileSelectorModal Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        current_profile: str,
        profiles: dict[str, ProfileConfig],
        **kwargs: Any,
    ) -> None:
        """Initialize the modal.

        Args:
            current_profile: Name of currently active profile
            profiles: Dictionary of available profiles
        """
        super().__init__(**kwargs)
        self.current_profile = current_profile
        self.profiles = profiles
        self.filtered_profiles: dict[str, ProfileConfig] = {}
        self._table: DataTable[Any] | None = None
        self._profile_map: dict[str, ProfileConfig] = {}  # row_key -> ProfileConfig
        log.info(
            f"ProfileSelectorModal: Initialized with current_profile={current_profile}"
        )

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical(id="modal-wrapper"):
            # Header
            yield Label("Select Profile", classes="modal-header")

            # Search/filter input
            yield Input(
                placeholder="Search profiles by name or description...",
                id="search-input",
            )

            # DataTable for profiles
            yield DataTable(id="profiles-table", zebra_stripes=True, cursor_type="row")

            # Info label
            yield Label("Enter: select · Escape: cancel", classes="info-label")

            # Action buttons
            with Horizontal(id="button-row"):
                yield Button("Select", variant="primary", id="select-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    async def on_mount(self) -> None:
        """Load profiles and populate table when mounted."""
        log.info("ProfileSelectorModal: on_mount called, populating profiles")

        # Initialize table
        self._table = self.query_one("#profiles-table", DataTable)
        self._table.add_column("Name")
        self._table.add_column("Description")
        self._table.add_column("Model")
        self._table.cursor_type = "row"
        self._table.focus()

        # Populate table
        self._populate_table()

    def _populate_table(self, search_query: str = "") -> None:
        """Populate or refresh the table with profiles.

        Args:
            search_query: Optional search query to filter profiles
        """
        if not self._table:
            return

        # Clear existing rows
        self._table.clear()
        self._profile_map.clear()

        # Apply search filter if provided
        profiles_to_display = self.profiles
        if search_query:
            query_lower = search_query.lower()
            profiles_to_display = {
                name: profile
                for name, profile in self.profiles.items()
                if query_lower in name.lower()
                or query_lower in profile.description.lower()
            }

        # Add rows, sorting by name
        for name in sorted(profiles_to_display.keys()):
            profile = profiles_to_display[name]
            row_key = name

            self._profile_map[row_key] = profile

            # Format columns
            is_current = name == self.current_profile
            name_col = f"✓ {name}" if is_current else f"  {name}"
            description_col = (
                profile.description[:40] + "..."
                if len(profile.description) > 40
                else profile.description
            )
            model_col = profile.model.model

            self._table.add_row(name_col, description_col, model_col, key=row_key)

            # Highlight current profile row
            if is_current:
                # Move cursor to current profile
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
            f"ProfileSelectorModal: Populated table with {len(profiles_to_display)} profiles"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self._populate_table(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key)."""
        if event.row_key:
            selected_profile = str(event.row_key.value)
            log.info(f"ProfileSelectorModal: Selected profile '{selected_profile}'")
            self.dismiss(selected_profile)

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
            selected_profile = str(row_key)
            log.info(f"ProfileSelectorModal: Selected profile '{selected_profile}'")
            self.dismiss(selected_profile)

    def action_cancel(self) -> None:
        """Handle cancel action (Escape key)."""
        log.info("ProfileSelectorModal: Cancel action")
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "select-btn":
            self.action_select()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
