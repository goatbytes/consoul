"""ContextualTopBar widget - command center for Consoul TUI.

Provides a three-zone top bar with branding, status display, and quick actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Click

__all__ = ["ContextualTopBar"]


class ContextualTopBar(Static):
    """A context-aware top bar that serves as the command center for Consoul TUI.

    This widget provides:
    - Three responsive zones: Branding/Status, Actions, System Info
    - Context-aware status display (model, profile, conversation count)
    - Quick action triggers for settings, help, theme switching
    - Responsive design that adapts to terminal width
    """

    DEFAULT_CSS = """
    ContextualTopBar {
        dock: top;
        width: 100%;
        height: 3;
        background: $primary;
        margin: 0;
        padding: 0;
        border: none;
    }

    ContextualTopBar .top-bar-container {
        width: 100%;
        height: 100%;
        layout: horizontal;
        margin: 0;
        padding: 0 1;
        align: left middle;
    }

    /* Left Zone - Branding/Status */
    ContextualTopBar .brand-zone {
        width: auto;
        height: 100%;
        align: left middle;
        layout: horizontal;
        background: transparent;
        margin: 0;
        padding: 0 2 0 0;
    }

    ContextualTopBar .brand-logo {
        color: $accent;
        text-style: bold;
        background: transparent;
        margin: 0 1 0 0;
    }

    ContextualTopBar .conversation-info {
        color: white 70%;
        text-style: italic;
        background: transparent;
        margin: 0 0 0 1;
    }

    /* Center Zone - Actions/Search */
    ContextualTopBar .action-zone {
        width: 1fr;
        height: 100%;
        align: center middle;
        layout: horizontal;
        background: transparent;
        margin: 0;
        padding: 0 1;
    }

    ContextualTopBar .search-placeholder {
        color: white 50%;
        text-style: dim;
        background: transparent;
        margin: 0 2;
    }

    /* Right Zone - System Info */
    ContextualTopBar .status-zone {
        width: auto;
        height: 100%;
        align: right middle;
        layout: horizontal;
        background: transparent;
        margin: 0;
        padding: 0 0 0 2;
    }

    ContextualTopBar .status-label {
        color: white 80%;
        margin: 0 1;
        background: transparent;
    }

    ContextualTopBar .action-button {
        margin: 0 1;
        background: transparent;
        color: white 80%;
        text-style: normal;
        padding: 0 1;
    }

    ContextualTopBar .action-button:hover {
        background: $primary-lighten-1;
        color: $accent;
        text-style: bold;
    }

    ContextualTopBar .streaming-indicator {
        color: $success;
        text-style: bold;
        margin: 0 1;
        background: transparent;
    }

    /* Responsive - hide non-essential on narrow terminals */
    ContextualTopBar.-narrow .conversation-info {
        display: none;
    }

    ContextualTopBar.-narrow .search-placeholder {
        display: none;
    }
    """

    # Reactive properties for dynamic content
    current_model: reactive[str] = reactive("")
    current_profile: reactive[str] = reactive("default")
    conversation_count: reactive[int] = reactive(0)
    streaming: reactive[bool] = reactive(False)
    terminal_width: reactive[int] = reactive(80)

    # Custom message types
    class SearchRequested(Message):
        """Message sent when search is requested."""

    class SettingsRequested(Message):
        """Message sent when settings button is clicked."""

    class HelpRequested(Message):
        """Message sent when help button is clicked."""

    class ModelSelectionRequested(Message):
        """Message sent when model selector is clicked."""

    class ThemeSwitchRequested(Message):
        """Message sent when theme switch is requested."""

    def on_mount(self) -> None:
        """Initialize the top bar when mounted."""
        # Update terminal width for responsive design
        self._update_terminal_width()

    def on_resize(self) -> None:
        """Handle terminal resize for responsive design."""
        self._update_terminal_width()

    def _update_terminal_width(self) -> None:
        """Update terminal width and apply responsive classes."""
        if not hasattr(self, "app") or not hasattr(self.app, "size"):
            return

        size = self.app.size
        self.terminal_width = size.width

        # Remove existing responsive classes
        self.remove_class("-narrow", "-wide")

        # Apply responsive classes based on width
        if size.width < 100:
            self.add_class("-narrow")
        elif size.width > 140:
            self.add_class("-wide")

    def compose(self) -> ComposeResult:
        """Compose the three-zone top bar layout."""
        with Horizontal(classes="top-bar-container"):
            # Zone 1: Branding/Status (Left)
            with Horizontal(classes="brand-zone", id="brand-zone"):
                yield from self._compose_brand_zone()

            # Zone 2: Actions/Search (Center)
            with Horizontal(classes="action-zone", id="action-zone"):
                yield from self._compose_action_zone()

            # Zone 3: System Info (Right)
            with Horizontal(classes="status-zone", id="status-zone"):
                yield from self._compose_status_zone()

    def _compose_brand_zone(self) -> ComposeResult:
        """Compose the branding/status zone."""
        # Consoul logo
        yield Label("🤖 Consoul", classes="brand-logo", id="brand-logo")

        # Conversation count indicator
        count_text = (
            f"{self.conversation_count} conversations"
            if self.conversation_count
            else "No conversations"
        )
        yield Label(count_text, classes="conversation-info", id="conversation-info")

    def _compose_action_zone(self) -> ComposeResult:
        """Compose the action/search zone."""
        # Placeholder for search bar (SOUL-45 will implement)
        yield Label(
            "[Search coming in SOUL-45]",
            classes="search-placeholder",
            id="search-placeholder",
        )

    def _compose_status_zone(self) -> ComposeResult:
        """Compose the system info zone."""
        # Streaming indicator
        if self.streaming:
            yield Label(
                "⚡ Streaming", classes="streaming-indicator", id="streaming-indicator"
            )

        # Model info (clickable for SOUL-44)
        model_text = f"Model: {self.current_model or 'default'}"
        model_label = Label(
            model_text, classes="status-label action-button", id="model-label"
        )
        model_label.can_focus = True
        yield model_label

        # Profile info
        profile_text = f"Profile: {self.current_profile}"
        yield Label(profile_text, classes="status-label", id="profile-label")

        # Quick action buttons
        settings_btn = Label("⚙️", classes="action-button", id="settings-btn")
        settings_btn.can_focus = True
        yield settings_btn

        help_btn = Label("?", classes="action-button", id="help-btn")
        help_btn.can_focus = True
        yield help_btn

        theme_btn = Label("🎨", classes="action-button", id="theme-btn")
        theme_btn.can_focus = True
        yield theme_btn

    def watch_conversation_count(self, count: int) -> None:
        """React to conversation count changes."""
        try:
            conv_info = self.query_one("#conversation-info", Label)
            conv_info.update(f"{count} conversations" if count else "No conversations")
        except Exception:
            pass

    def watch_current_model(self, model: str) -> None:
        """React to model changes."""
        try:
            model_label = self.query_one("#model-label", Label)
            model_label.update(f"Model: {model or 'default'}")
        except Exception:
            pass

    def watch_current_profile(self, profile: str) -> None:
        """React to profile changes."""
        try:
            profile_label = self.query_one("#profile-label", Label)
            profile_label.update(f"Profile: {profile}")
        except Exception:
            pass

    def watch_streaming(self, is_streaming: bool) -> None:
        """React to streaming state changes."""
        # Trigger recompose to show/hide streaming indicator
        self.refresh(recompose=True)

    async def on_click(self, event: Click) -> None:
        """Handle click events on action buttons."""
        # Determine which element was clicked
        target_id = (
            event.control.id
            if hasattr(event, "control") and hasattr(event.control, "id")
            else None
        )

        if target_id == "settings-btn":
            self.post_message(self.SettingsRequested())
        elif target_id == "help-btn":
            self.post_message(self.HelpRequested())
        elif target_id == "theme-btn":
            self.post_message(self.ThemeSwitchRequested())
        elif target_id == "model-label":
            self.post_message(self.ModelSelectionRequested())
