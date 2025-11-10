"""MessageBubble widget for displaying chat messages with markdown rendering.

This module provides a widget that wraps individual messages with role-specific
styling, markdown formatting, and optional metadata display.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from rich.console import Group, RenderableType
from rich.markdown import Markdown
from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

__all__ = ["MessageBubble"]


class MessageBubble(Static):
    """Message bubble widget with role-specific styling and markdown rendering.

    Displays a single message with appropriate styling based on the sender role.
    Supports markdown formatting and optional metadata display (timestamp, tokens).

    Attributes:
        role: Message role (user, assistant, system, or error)
        content_text: Message content
        timestamp: Message timestamp
        token_count: Optional token count for the message
        show_metadata: Whether to display metadata footer
    """

    # Reactive state
    role: reactive[str] = reactive("user")

    def __init__(
        self,
        content: str,
        role: Literal["user", "assistant", "system", "error"] = "user",
        timestamp: datetime | None = None,
        token_count: int | None = None,
        show_metadata: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize MessageBubble widget.

        Args:
            content: Message text content (supports markdown)
            role: Message role determining styling
            timestamp: Message timestamp (defaults to now)
            token_count: Optional token count to display
            show_metadata: Whether to show metadata footer
            **kwargs: Additional arguments passed to Static
        """
        super().__init__(**kwargs)
        # Set attributes before setting reactive role (which triggers watchers)
        self.content_text = content
        self.timestamp = timestamp or datetime.now()
        self.token_count = token_count
        self.show_metadata = show_metadata
        self._markdown_failed = False
        # Set role last (triggers watcher which needs other attributes)
        self.role = role

    def on_mount(self) -> None:
        """Initialize message bubble on mount."""
        self._update_styling()
        self._render_message()

    def _update_styling(self) -> None:
        """Update widget styling based on role.

        Applies role-specific CSS class and sets border title.
        """
        # Remove all role classes first
        for cls in [
            "message-user",
            "message-assistant",
            "message-system",
            "message-error",
        ]:
            self.remove_class(cls)

        # Add current role class
        self.add_class("message")
        self.add_class(f"message-{self.role}")

        # Set border title based on role
        role_titles = {
            "user": "You",
            "assistant": "Assistant",
            "system": "System",
            "error": "Error",
        }
        self.border_title = role_titles.get(self.role, "Message")

    def _render_message(self) -> None:
        """Render message content with markdown and optional metadata."""
        # Render markdown content
        try:
            content_renderable: RenderableType = Markdown(self.content_text)
        except Exception:
            # Fallback to plain text if markdown fails
            self._markdown_failed = True
            content_renderable = Text(self.content_text)

        # Add metadata footer if enabled
        if self.show_metadata:
            metadata = self._build_metadata_footer()
            # Combine content and metadata using Group
            combined = Group(content_renderable, metadata)
            self.update(combined)
        else:
            self.update(content_renderable)

    def _build_metadata_footer(self) -> Text:
        """Build metadata footer with timestamp and optional token count.

        Returns:
            Rich Text object with styled metadata
        """
        footer = Text()

        # Add timestamp
        time_str = self.timestamp.strftime("%H:%M:%S")
        footer.append("🕐 ", style="dim")
        footer.append(time_str, style="dim italic")

        # Add token count if available
        if self.token_count is not None:
            footer.append(" │ ", style="dim")
            footer.append("🎯 ", style="bold")
            footer.append(f"{self.token_count} tokens", style="bold cyan")

        return footer

    def watch_role(self, new_role: str) -> None:
        """Update styling when role changes.

        Called automatically when the role reactive property changes.

        Args:
            new_role: New role value
        """
        self._update_styling()
        self._render_message()

    def update_content(self, new_content: str) -> None:
        """Update message content and re-render.

        Args:
            new_content: New message content
        """
        self.content_text = new_content
        self._markdown_failed = False
        self._render_message()
