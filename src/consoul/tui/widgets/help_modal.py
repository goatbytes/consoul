"""HelpModal - Modal dialog displaying keyboard shortcuts and help information."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, TabbedContent, TabPane

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["HelpModal"]


class HelpModal(ModalScreen[None]):
    """Modal dialog displaying keyboard shortcuts and application information.

    Shows:
    - Keyboard shortcuts organized by category
    - Current configuration (theme, profile, model)
    - Documentation links and version information
    """

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
    }

    HelpModal > Vertical {
        width: 80;
        height: auto;
        max-height: 85%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    HelpModal .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
    }

    HelpModal TabbedContent {
        width: 100%;
        height: auto;
        max-height: 30;
        background: transparent;
        border: none;
        margin: 0 0 1 0;
    }

    HelpModal TabPane {
        padding: 1;
    }

    HelpModal VerticalScroll {
        width: 100%;
        height: auto;
        max-height: 28;
    }

    HelpModal .section-title {
        width: 100%;
        text-style: bold;
        color: $accent;
        margin: 1 0 0 0;
    }

    HelpModal .shortcut-row {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin: 0 0 0 0;
    }

    HelpModal .shortcut-key {
        width: 30%;
        content-align: left middle;
        color: $primary;
        text-style: bold;
    }

    HelpModal .shortcut-dots {
        width: 5%;
        content-align: center middle;
        color: $text-muted;
    }

    HelpModal .shortcut-desc {
        width: 65%;
        content-align: left middle;
        color: $text;
    }

    HelpModal .info-row {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin: 0 0 1 0;
    }

    HelpModal .info-label {
        width: 30%;
        content-align: left middle;
        color: $accent;
        text-style: bold;
    }

    HelpModal .info-value {
        width: 70%;
        content-align: left middle;
        color: $text;
    }

    HelpModal .link {
        width: 100%;
        color: $secondary;
        text-style: italic;
        margin: 0 0 1 0;
    }

    HelpModal .button-container {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin: 1 0 0 0;
    }

    HelpModal Button {
        min-width: 16;
        margin: 0 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Close", show=False),
    ]

    def __init__(
        self,
        theme: str,
        profile: str,
        model: str,
        **kwargs: Any,
    ) -> None:
        """Initialize help modal.

        Args:
            theme: Current theme name
            profile: Current profile name
            model: Current model name
            **kwargs: Additional arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.theme = theme
        self.profile = profile
        self.model = model

    def compose(self) -> ComposeResult:
        """Compose the help modal layout."""
        with Vertical():
            yield Label("Consoul Help", classes="modal-title")

            with TabbedContent():
                with TabPane("Keyboard Shortcuts"), VerticalScroll():
                    yield from self._compose_shortcuts_tab()

                with TabPane("About"), VerticalScroll():
                    yield from self._compose_about_tab()

            # Close button
            with Horizontal(classes="button-container"):
                yield Button("Close", variant="primary", id="close-button")

    def _compose_shortcuts_tab(self) -> ComposeResult:
        """Compose the keyboard shortcuts tab."""
        # Essential shortcuts
        yield Label("Essential", classes="section-title")
        yield from self._shortcut_row("Q, Ctrl+C", "Quit")

        # Conversation shortcuts
        yield Label("Conversation", classes="section-title")
        yield from self._shortcut_row("Ctrl+N", "New Chat")
        yield from self._shortcut_row("Ctrl+L", "Clear")
        yield from self._shortcut_row("Escape", "Cancel Stream")

        # Navigation shortcuts
        yield Label("Navigation", classes="section-title")
        yield from self._shortcut_row("Ctrl+P", "Switch Profile")
        yield from self._shortcut_row("Ctrl+M", "Switch Model")
        yield from self._shortcut_row("Ctrl+E", "Export Conversation")
        yield from self._shortcut_row("Ctrl+I", "Import Conversation")
        yield from self._shortcut_row("Ctrl+S", "Search History")
        yield from self._shortcut_row("/", "Focus Input")

        # UI shortcuts
        yield Label("UI", classes="section-title")
        yield from self._shortcut_row("Ctrl+,", "Settings")
        yield from self._shortcut_row("F1", "Help (this screen)")

    def _compose_about_tab(self) -> ComposeResult:
        """Compose the about tab with current configuration."""
        # Current configuration
        yield Label("Current Configuration", classes="section-title")

        with Horizontal(classes="info-row"):
            yield Label("Theme:", classes="info-label")
            yield Label(self.theme, classes="info-value")

        with Horizontal(classes="info-row"):
            yield Label("Profile:", classes="info-label")
            yield Label(self.profile, classes="info-value")

        with Horizontal(classes="info-row"):
            yield Label("Model:", classes="info-label")
            yield Label(self.model, classes="info-value")

        # Documentation
        yield Label("Documentation", classes="section-title")
        yield Static(
            "GitHub: https://github.com/goatbytes/consoul",
            classes="link",
        )
        yield Static(
            "Documentation: https://docs.goatbytes.io/consoul",
            classes="link",
        )
        yield Static(
            "Issues: https://github.com/goatbytes/consoul/issues",
            classes="link",
        )

        # About
        yield Label("About", classes="section-title")
        yield Static(
            "Consoul is an AI-powered terminal assistant built with LangChain and Textual.",
            classes="info-value",
        )
        yield Static(
            "Created by GoatBytes.IO",
            classes="info-value",
        )

    def _shortcut_row(self, key: str, description: str) -> ComposeResult:
        """Create a shortcut row with key and description.

        Args:
            key: Keyboard shortcut(s)
            description: Description of what the shortcut does

        Yields:
            Widgets for the shortcut row
        """
        with Horizontal(classes="shortcut-row"):
            yield Label(key, classes="shortcut-key")
            yield Label("·", classes="shortcut-dots")
            yield Label(description, classes="shortcut-desc")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-button":
            self.dismiss(None)

    def action_close(self) -> None:
        """Close the help modal."""
        self.dismiss(None)
