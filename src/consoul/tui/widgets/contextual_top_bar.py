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

from consoul.tui.widgets.search_bar import SearchBar

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
        color: auto;
        text-style: bold;
        background: transparent;
        margin: 0 1 0 0;
    }

    ContextualTopBar .conversation-info {
        color: auto 70%;
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

    ContextualTopBar .search-bar {
        width: 1fr;
        max-width: 60;
        height: 1;
        margin: 0;
        padding: 0;
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
        color: auto 80%;
        margin: 0 1;
        background: transparent;
    }

    ContextualTopBar .action-button {
        margin: 0 1;
        background: transparent;
        color: auto 80%;
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
    current_provider: reactive[str] = reactive("")
    current_model: reactive[str] = reactive("")
    current_profile: reactive[str] = reactive("default")
    conversation_count: reactive[int] = reactive(0)
    streaming: reactive[bool] = reactive(False)
    terminal_width: reactive[int] = reactive(80)
    tools_enabled: reactive[int] = reactive(0)
    tools_total: reactive[int] = reactive(13)  # Total available tools
    highest_risk: reactive[str] = reactive(
        "none"
    )  # "safe", "caution", "dangerous", "none"

    # Custom message types
    class SearchChanged(Message):
        """Message sent when search query changes."""

        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    class SearchCleared(Message):
        """Message sent when search is cleared."""

    class SettingsRequested(Message):
        """Message sent when settings button is clicked."""

    class HelpRequested(Message):
        """Message sent when help button is clicked."""

    class ModelSelectionRequested(Message):
        """Message sent when model selector is clicked."""

    class ProfileSelectionRequested(Message):
        """Message sent when profile selector is clicked."""

    class ToolsRequested(Message):
        """Message sent when tools button is clicked."""

    class SidebarToggleRequested(Message):
        """Message sent when conversation count is clicked to toggle sidebar."""

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

    def _get_tool_status_icon(self) -> str:
        """Get tool status icon based on enabled state and risk level.

        Returns:
            Icon representing current tool status
        """
        if self.tools_enabled == 0:
            return "⛨"  # No tools

        # Show icon based on risk level
        if self.highest_risk == "dangerous":
            return "[red]⚒[/red]"  # Red for dangerous
        elif self.highest_risk == "caution":
            return "[yellow]⛏[/yellow]"  # Yellow for caution
        else:
            return "⚒"  # Tools icon for safe

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
        yield Label("⟡ C𝙤ns𝙤ul", classes="brand-logo", id="brand-logo")

        # Conversation count indicator (clickable to toggle sidebar)
        count_text = (
            f"{self.conversation_count} conversations"
            if self.conversation_count
            else "No conversations"
        )
        conv_label = Label(
            count_text,
            classes="conversation-info action-button",
            id="conversation-info",
        )
        conv_label.can_focus = True
        yield conv_label

    def _compose_action_zone(self) -> ComposeResult:
        """Compose the action/search zone."""
        # Search bar widget
        yield SearchBar(id="search-bar", classes="search-bar")

    def _compose_status_zone(self) -> ComposeResult:
        """Compose the system info zone."""
        # Streaming indicator
        if self.streaming:
            yield Label(
                "⚡ Streaming", classes="streaming-indicator", id="streaming-indicator"
            )

        # Model info (clickable) - shows provider:model format
        provider_display = (
            self.current_provider.title() if self.current_provider else "?"
        )
        model_display = self._get_model_display_name(
            self.current_model, self.current_provider
        )
        model_text = f"◉ {provider_display}: {model_display}"
        model_label = Label(
            model_text, classes="status-label action-button", id="model-label"
        )
        model_label.can_focus = True
        yield model_label

        # Profile info (clickable)
        profile_text = f"Profile: {self.current_profile}"
        profile_label = Label(
            profile_text, classes="status-label action-button", id="profile-label"
        )
        profile_label.can_focus = True
        yield profile_label

        # Quick action buttons
        # Tool status button (shows icon based on enabled tools and risk)
        tool_icon = self._get_tool_status_icon()
        tools_btn = Label(tool_icon, classes="action-button", id="tools-btn")
        # tools_btn = Label("⚒", classes="action-button", id="tools-btn")
        tools_btn.can_focus = True
        yield tools_btn

        settings_btn = Label("⚙", classes="action-button", id="settings-btn")
        settings_btn.can_focus = True
        yield settings_btn

        help_btn = Label("?", classes="action-button", id="help-btn")
        help_btn.can_focus = True
        yield help_btn

    def watch_conversation_count(self, count: int) -> None:
        """React to conversation count changes."""
        try:
            conv_info = self.query_one("#conversation-info", Label)
            conv_info.update(f"{count} conversations" if count else "No conversations")
        except Exception:
            pass

    def watch_current_provider(self, provider: str) -> None:
        """React to provider changes."""
        if self.is_mounted:
            self._update_model_label()

    def watch_current_model(self, model: str) -> None:
        """React to model changes."""
        if self.is_mounted:
            self._update_model_label()

    def _get_model_display_name(self, model: str, provider: str) -> str:
        """Get a clean display name for the model.

        Args:
            model: The model identifier (may be a file path)
            provider: The provider name

        Returns:
            A user-friendly display name
        """
        if not model:
            return "default"

        # For file paths (GGUF, MLX), extract just the filename or last directory
        if "/" in model or "\\" in model:
            from pathlib import Path

            path = Path(model)

            # For GGUF files, return just the filename
            if path.suffix == ".gguf":
                return path.name

            # For MLX models (directories), return the last two parts (org/model)
            parts = path.parts
            if len(parts) >= 2:
                # Return last two parts: e.g., "mlx-community/gemma-3-27b-it-qat-4bit"
                return f"{parts[-2]}/{parts[-1]}"
            return path.name

        return model

    def _update_model_label(self) -> None:
        """Update the model label with provider:model format."""
        try:
            model_label = self.query_one("#model-label", Label)
            provider_display = (
                self.current_provider.title() if self.current_provider else "?"
            )
            model_display = self._get_model_display_name(
                self.current_model, self.current_provider
            )
            model_label.update(f"◉ {provider_display}: {model_display}")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error updating model label: {e}", exc_info=True)

    def watch_current_profile(self, profile: str) -> None:
        """React to profile changes."""
        if not self.is_mounted:
            return

        try:
            profile_label = self.query_one("#profile-label", Label)
            profile_label.update(f"Profile: {profile}")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error updating profile label: {e}", exc_info=True)

    def watch_streaming(self, is_streaming: bool) -> None:
        """React to streaming state changes."""
        # Trigger recompose to show/hide streaming indicator
        self.refresh(recompose=True)

    def watch_tools_enabled(self, count: int) -> None:
        """React to tool count changes."""
        if not self.is_mounted:
            return

        try:
            tool_btn = self.query_one("#tools-btn", Label)
            tool_btn.update(self._get_tool_status_icon())
        except Exception:
            pass

    def watch_highest_risk(self, risk: str) -> None:
        """React to risk level changes."""
        if not self.is_mounted:
            return

        try:
            tool_btn = self.query_one("#tools-btn", Label)
            tool_btn.update(self._get_tool_status_icon())
        except Exception:
            pass

    async def on_click(self, event: Click) -> None:
        """Handle click events on action buttons."""
        # Determine which element was clicked
        target_id = (
            event.control.id
            if hasattr(event, "control")
            and event.control is not None
            and hasattr(event.control, "id")
            else None
        )

        if target_id == "conversation-info":
            self.post_message(self.SidebarToggleRequested())
        elif target_id == "tools-btn":
            self.post_message(self.ToolsRequested())
        elif target_id == "settings-btn":
            self.post_message(self.SettingsRequested())
        elif target_id == "help-btn":
            self.post_message(self.HelpRequested())
        elif target_id == "model-label":
            self.post_message(self.ModelSelectionRequested())
        elif target_id == "profile-label":
            self.post_message(self.ProfileSelectionRequested())
