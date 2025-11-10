"""Main Consoul TUI application.

This module provides the primary ConsoulApp class that implements the Textual
terminal user interface for interactive AI conversations.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Header

if TYPE_CHECKING:
    from textual.binding import BindingType

from consoul.tui.config import TuiConfig
from consoul.tui.css.themes import load_theme

__all__ = ["ConsoulApp"]


class ConsoulApp(App[None]):
    """Main Consoul Terminal User Interface application.

    Provides an interactive chat interface with streaming AI responses,
    conversation history, and keyboard-driven navigation.
    """

    CSS_PATH = "css/main.tcss"
    TITLE = "Consoul - AI Terminal Assistant"
    SUB_TITLE = "Powered by LangChain"

    BINDINGS: ClassVar[list[BindingType]] = [
        # Essential
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True, show=False),
        # Conversation
        Binding("ctrl+n", "new_conversation", "New Chat"),
        Binding("ctrl+l", "clear_conversation", "Clear"),
        Binding("escape", "cancel_stream", "Cancel", show=False),
        # Navigation
        Binding("ctrl+p", "switch_profile", "Profile", show=False),
        Binding("ctrl+m", "switch_model", "Model", show=False),
        Binding("ctrl+e", "export_conversation", "Export", show=False),
        Binding("ctrl+s", "search_history", "Search", show=False),
        Binding("/", "focus_input", "Input", show=False),
        # UI
        Binding("ctrl+comma", "settings", "Settings", show=False),
        Binding("ctrl+t", "cycle_theme", "Theme", show=False),
        Binding("f1", "help", "Help", show=False),
    ]

    # Reactive state
    current_profile: reactive[str] = reactive("default")
    current_model: reactive[str] = reactive("")
    conversation_id: reactive[str | None] = reactive(None)
    streaming: reactive[bool] = reactive(False)

    def __init__(
        self, config: TuiConfig | None = None, test_mode: bool = False
    ) -> None:
        """Initialize the Consoul TUI application.

        Args:
            config: TUI configuration (uses defaults if None)
            test_mode: Enable test mode (auto-exit for testing)
        """
        super().__init__()
        self.config = config or TuiConfig()
        self.test_mode = test_mode

        # Store original GC state for cleanup (library-first design)
        self._original_gc_enabled = gc.isenabled()

        # GC management will be set up in on_mount (after message pump starts)
        self._gc_interval_timer: object | None = None

    def on_mount(self) -> None:
        """Initialize app after mounting (message pump is running).

        Sets up GC management and validates theme.
        """
        # Validate theme (can safely notify now that message pump is running)
        try:
            _ = load_theme(self.config.theme)  # type: ignore[arg-type]
        except FileNotFoundError:
            self.notify(
                f"Theme '{self.config.theme}' not found, using default",
                severity="warning",
            )

        # Set up GC management (streaming-aware mode from research)
        if self.config.gc_mode == "streaming-aware":
            gc.disable()
            self._gc_interval_timer = self.set_interval(
                self.config.gc_interval_seconds, self._idle_gc
            )

    def on_unmount(self) -> None:
        """Cleanup when app unmounts (library-first design).

        Restores original GC state to avoid affecting embedding applications.
        """
        # Restore original GC state
        if self._original_gc_enabled:
            gc.enable()
        else:
            gc.disable()

    def compose(self) -> ComposeResult:
        """Compose the UI layout.

        Yields:
            Widgets to display in the app
        """
        from consoul.tui.widgets import ChatView

        yield Header()
        yield ChatView()
        yield Footer()

    def _idle_gc(self) -> None:
        """Periodic garbage collection when not streaming.

        Called on interval defined by config.gc_interval_seconds.
        Only collects when not actively streaming.
        """
        if not self.streaming:
            gc.collect(generation=self.config.gc_generation)

    # Action handlers (placeholders for Phase 2+)

    def action_new_conversation(self) -> None:
        """Start a new conversation."""
        self.notify("New conversation (placeholder)")

    def action_clear_conversation(self) -> None:
        """Clear current conversation."""
        self.notify("Clear conversation (placeholder)")

    def action_cancel_stream(self) -> None:
        """Cancel active streaming."""
        if self.streaming:
            self.streaming = False
            self.notify("Streaming cancelled")

    def action_switch_profile(self) -> None:
        """Show profile selection modal."""
        self.notify("Profile switcher (Phase 3)")

    def action_switch_model(self) -> None:
        """Show model selection modal."""
        self.notify("Model switcher (Phase 3)")

    def action_export_conversation(self) -> None:
        """Show export modal."""
        self.notify("Export (Phase 4)")

    def action_search_history(self) -> None:
        """Show search interface."""
        self.notify("Search (Phase 4)")

    def action_focus_input(self) -> None:
        """Focus the input area."""
        self.notify("Focus input (Phase 2)")

    def action_settings(self) -> None:
        """Show settings screen."""
        self.notify("Settings (Phase 4)")

    def action_cycle_theme(self) -> None:
        """Cycle to next theme."""
        self.notify("Theme cycling (Phase 4)")

    def action_help(self) -> None:
        """Show help modal."""
        self.notify("Help (Phase 4)")
