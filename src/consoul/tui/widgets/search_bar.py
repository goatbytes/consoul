"""SearchBar widget for searching conversation history."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.containers import Horizontal
from textual.widgets import Input, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Click

__all__ = ["SearchBar"]


class SearchBar(Static):
    """Search bar widget for filtering conversations.

    This widget provides a search input field integrated with the top bar design.
    It does NOT post messages on input changes to avoid focus/freezing issues.
    Instead, the parent app should poll get_search_query() on a timer.
    """

    DEFAULT_CSS = """
    SearchBar {
        width: 100%;
        height: 1;
        background: transparent;
        border: none;
        padding: 0;
        margin: 0;
    }

    SearchBar .search-container {
        width: 100%;
        height: 1;
        layout: horizontal;
        align: left middle;
        background: transparent;
        padding: 0;
        margin: 0;
    }

    /* Mode indicator */
    SearchBar .mode-indicator {
        width: 2;
        min-width: 2;
        height: 1;
        margin: 0 1 0 0;
        padding: 0;
        background: transparent;
        color: white 70%;
        text-align: center;
    }

    /* Search input - seamlessly integrated with toolbar */
    SearchBar .search-input {
        width: 1fr;
        background: $primary 120%;
        border: none;
        margin: 0;
        padding: 0 2;
        color: white;
    }

    SearchBar .search-input > .input--cursor {
        color: white;
        background: white 50%;
    }

    SearchBar .search-input > .input--placeholder {
        color: white 50%;
        text-style: italic;
    }

    SearchBar .search-input:focus {
        background: $accent 20%;
        color: white;
        text-style: none;
        border: none;
    }

    SearchBar .search-input:focus > .input--cursor {
        color: white;
        background: white;
    }

    /* Match counter */
    SearchBar .match-counter {
        width: auto;
        height: 1;
        color: white 70%;
        text-style: italic;
        background: transparent;
        margin: 0 2 0 0;
        padding: 0;
        text-align: right;
    }

    /* Clear button */
    SearchBar .clear-button {
        width: auto;
        min-width: 3;
        height: 1;
        background: transparent;
        color: white;
        text-style: bold;
        margin: 0;
        padding: 0;
        text-align: center;
    }

    SearchBar .clear-button:hover {
        background: transparent;
        color: $warning;
        text-style: bold;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the search bar."""
        super().__init__(**kwargs)
        self._search_query = ""
        self._match_count = 0

    def compose(self) -> ComposeResult:
        """Compose the search bar layout."""
        with Horizontal(classes="search-container"):
            # Mode indicator (search icon)
            yield Label("🔍", id="mode-indicator", classes="mode-indicator")

            # Search input field
            yield Input(
                placeholder="Search conversations...",
                id="search-input",
                classes="search-input",
            )

            # Match counter (initially hidden)
            yield Label("", id="match-counter", classes="match-counter")

            # Clear button (initially hidden)
            yield Static(" ✖ ", id="clear-button", classes="clear-button")

    def on_mount(self) -> None:
        """Initialize the search bar when mounted."""
        try:
            # Hide match counter and clear button initially
            self.query_one("#match-counter", Label).display = False
            self.query_one("#clear-button", Static).display = False
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes.

        IMPORTANT: Does NOT post messages to avoid focus/freeze issues.
        Parent app should poll get_search_query() instead.
        """
        if event.input.id == "search-input":
            self._search_query = event.value
            # Update clear button visibility
            try:
                clear_button = self.query_one("#clear-button", Static)
                clear_button.display = bool(event.value)
            except Exception:
                pass

    def on_click(self, event: Click) -> None:
        """Handle click events (clear button)."""
        if hasattr(event.widget, "id") and event.widget.id == "clear-button":
            try:
                # Clear the search
                search_input = self.query_one("#search-input", Input)
                search_input.value = ""
                self._search_query = ""
                self._match_count = 0

                # Hide UI elements
                self.query_one("#clear-button", Static).display = False
                self.query_one("#match-counter", Label).display = False

                # Stop event propagation
                event.stop()
            except Exception:
                pass

    def get_search_query(self) -> str:
        """Get the current search query.

        Returns:
            The current search query string
        """
        return self._search_query

    def update_match_count(self, count: int) -> None:
        """Update the match counter display.

        Args:
            count: The number of matching conversations
        """
        self._match_count = count

        try:
            match_counter = self.query_one("#match-counter", Label)

            if count > 0:
                # Show counter with proper singular/plural
                match_text = f"{count} result{'s' if count != 1 else ''}"
                match_counter.update(match_text)
                match_counter.display = True
            else:
                # Hide counter when no matches
                match_counter.display = False
        except Exception:
            pass
