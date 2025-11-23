"""MessageBubble widget for displaying chat messages with markdown rendering.

This module provides a widget that wraps individual messages with role-specific
styling, markdown formatting, and optional metadata display.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from rich.text import Text
from textual import on
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Collapsible, Markdown, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["MessageBubble"]


class MessageBubble(Container):
    """Message bubble widget with role-specific styling and markdown rendering.

    Displays a single message with appropriate styling based on the sender role.
    Supports markdown formatting and optional metadata display (timestamp, tokens).

    Attributes:
        role: Message role (user, assistant, system, or error)
        content_text: Message content
        timestamp: Message timestamp
        token_count: Optional token count for the message
        show_metadata: Whether to display metadata footer
        message_id: Database message ID for branching
    """

    class BranchRequested(Message):
        """Message sent when user requests to branch from this message.

        Attributes:
            message_id: The database message ID to branch from
        """

        def __init__(self, message_id: int) -> None:
            """Initialize BranchRequested message.

            Args:
                message_id: The message ID to branch from
            """
            super().__init__()
            self.message_id = message_id

    # Reactive state
    role: reactive[str] = reactive("user")

    def __init__(
        self,
        content: str,
        role: Literal["user", "assistant", "system", "error"] = "user",
        timestamp: datetime | None = None,
        token_count: int | None = None,
        show_metadata: bool = True,
        tool_calls: list[dict[str, Any]] | None = None,
        message_id: int | None = None,
        thinking_content: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize MessageBubble widget.

        Args:
            content: Message text content (supports markdown)
            role: Message role determining styling
            timestamp: Message timestamp (defaults to now)
            token_count: Optional token count to display
            show_metadata: Whether to show metadata footer
            tool_calls: Optional list of tool call data dicts (for assistant messages)
            message_id: Optional database message ID (for branching functionality)
            thinking_content: Optional AI reasoning/thinking content to display in collapsible section
            **kwargs: Additional arguments passed to Static
        """
        super().__init__(**kwargs)
        # Set attributes before setting reactive role (which triggers watchers)
        self.content_text = content
        self.timestamp = timestamp or datetime.now()
        self.token_count = token_count
        self.show_metadata = show_metadata
        self.tool_calls = tool_calls or []
        self.message_id = message_id
        self.thinking_content = thinking_content
        self._markdown_failed = False
        # Set role last (triggers watcher which needs other attributes)
        self.role = role

    def compose(self) -> ComposeResult:
        """Compose the message bubble with content and metadata."""
        # Add thinking section if present
        if self.thinking_content:
            with Collapsible(
                title="💭 Thinking",
                collapsed=True,
                collapsed_symbol="▶",
                expanded_symbol="▼",
                id="thinking-collapsible",
                classes="thinking-section",
            ):
                yield Markdown(self.thinking_content, classes="thinking-content")

        # Create markdown widget for content (supports clickable links)
        # Will fallback to Static with Text if markdown fails
        yield Markdown(id="message-content", classes="message-content")

        # Add metadata footer if enabled
        if self.show_metadata:
            with Horizontal(classes="message-metadata"):
                yield Static(id="metadata-text", classes="metadata-text")

                # Add tool calls button if assistant message has tools
                if self.tool_calls:
                    yield Button(
                        "🛠",
                        id="tools-button",
                        classes="tools-button",
                    )

                # Add branch button for assistant messages with message_id
                if self.role == "assistant" and self.message_id is not None:
                    yield Button(
                        "🔀",
                        id="branch-button",
                        classes="branch-button",
                        tooltip="Branch conversation from this point",
                    )

                yield Button("📋", id="copy-button", classes="copy-button")

    def on_mount(self) -> None:
        """Initialize message bubble on mount."""
        self._update_styling()
        # Wait a moment for child widgets to be available
        self.call_later(self._render_message)

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
        # Try to get child widgets - if they don't exist yet, schedule retry
        try:
            content_widget = self.query_one("#message-content", Markdown)
        except Exception:
            # Child widgets not available yet, retry later
            self.call_later(self._render_message)
            return

        # Update markdown widget with content
        # The Markdown widget handles parsing and rendering
        try:
            content_widget.update(self.content_text)
        except Exception:
            # If markdown fails, fallback to showing raw text
            # Replace with Static widget showing plain text
            self._markdown_failed = True
            content_widget.remove()
            static_widget = Static(
                Text(self.content_text), id="message-content", classes="message-content"
            )
            self.mount(static_widget, before=0)

        # Update metadata if present
        if self.show_metadata:
            try:
                metadata_text = self._build_metadata_text()
                metadata_widget = self.query_one("#metadata-text", Static)
                metadata_widget.update(metadata_text)
            except Exception:
                # Metadata widget not available yet
                pass

    def _build_metadata_text(self) -> Text:
        """Build metadata text with timestamp and optional token count.

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

    @on(Button.Pressed, "#copy-button")
    async def copy_to_clipboard(self) -> None:
        """Copy message content to clipboard when copy button is pressed."""
        import pyperclip

        try:
            pyperclip.copy(self.content_text)
            # Show notification
            self.app.notify("Message copied to clipboard!", severity="information")
        except Exception as e:
            self.app.notify(f"Failed to copy: {e}", severity="error")

    @on(Button.Pressed, "#tools-button")
    async def show_tool_details(self) -> None:
        """Show tool call details modal when tools button is pressed."""
        from consoul.tui.widgets.tool_call_details_modal import ToolCallDetailsModal

        if self.tool_calls:
            modal = ToolCallDetailsModal(tool_calls=self.tool_calls)
            await self.app.push_screen(modal)

    @on(Button.Pressed, "#branch-button")
    async def request_branch(self) -> None:
        """Request to branch conversation from this message."""
        if self.message_id is not None:
            self.post_message(self.BranchRequested(self.message_id))

    @on(Markdown.LinkClicked)
    def handle_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Handle markdown link clicks by opening in browser.

        Args:
            event: LinkClicked event containing the URL
        """
        import webbrowser

        try:
            # Open the link in the default browser
            webbrowser.open(event.href)
            self.app.notify(f"Opening: {event.href}", severity="information", timeout=2)
        except Exception as e:
            self.app.notify(f"Failed to open link: {e}", severity="error")

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
