"""ConversationList widget for displaying conversation history sidebar.

This module provides a virtualized conversation list using Textual's DataTable
with support for lazy loading and FTS5 full-text search for performance with
1000+ conversations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.coordinate import Coordinate
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label

from consoul.tui.widgets.center_middle import CenterMiddle

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.ai.database import ConversationDatabase

__all__ = ["ConversationList", "RenameConversationModal"]


class ConversationList(Container):
    """Conversation history sidebar with virtualized list.

    Displays conversation titles with search and lazy loading for performance.
    Uses DataTable's built-in virtualization to handle large datasets efficiently.

    Attributes:
        conversation_count: Total number of conversations loaded
        selected_id: Currently selected conversation ID
    """

    class ConversationSelected(Message):
        """Message sent when a conversation is selected.

        Attributes:
            conversation_id: The ID of the selected conversation
        """

        def __init__(self, conversation_id: str) -> None:
            """Initialize ConversationSelected message.

            Args:
                conversation_id: The conversation ID that was selected
            """
            super().__init__()
            self.conversation_id = conversation_id

    # Reactive state
    conversation_count: reactive[int] = reactive(0)
    selected_id: reactive[str | None] = reactive(None)

    # Key bindings
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("f2", "rename_conversation", "Rename", show=False),
    ]

    INITIAL_LOAD = 50  # Conversations to load initially
    LAZY_LOAD_THRESHOLD = 10  # Rows from bottom to trigger lazy load

    def __init__(self, db: ConversationDatabase, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Initialize ConversationList widget.

        Args:
            db: ConversationDatabase instance for data access
            **kwargs: Additional keyword arguments passed to Container
        """
        super().__init__(**kwargs)
        self.db = db
        self.loaded_count = 0
        self._is_searching = False
        self._renaming = False

    def compose(self) -> ComposeResult:
        """Compose conversation list widgets.

        Yields:
            DataTable widget for displaying conversations and empty state label
        """
        # Empty state message (shown when no conversations exist)
        with CenterMiddle(id="empty-conversation-label"):
            yield Vertical(
                Label("[dim i]No conversations yet[/]"),
                Label(""),
                Label("[dim]Start a new conversation by typing a message below[/]"),
                classes="empty-state-content",
            )

        # Conversation table
        self.table: DataTable[str] = DataTable(cursor_type="row", zebra_stripes=True)
        yield self.table

    def on_mount(self) -> None:
        """Initialize conversation list on mount.

        Sets up table columns, styling, and loads initial conversations.
        """
        self.border_title = "Conversations"
        self.add_class("conversation-list")

        # Setup table columns (single column, no headers)
        self.table.add_column("Title", key="title")
        self.table.show_header = False

        # Load initial conversations asynchronously
        self.run_worker(self.load_conversations(), exclusive=True)

    async def load_conversations(self, limit: int | None = None) -> None:
        """Load conversations from database asynchronously to avoid blocking UI.

        Args:
            limit: Number of conversations to load (default: INITIAL_LOAD)
        """
        limit = limit or self.INITIAL_LOAD

        # Fetch from database in executor to avoid blocking
        import asyncio

        loop = asyncio.get_event_loop()
        conversations = await loop.run_in_executor(
            None,
            self.db.list_conversations,
            limit,
            self.loaded_count,
        )

        # Add rows to table
        for conv in conversations:
            # Get title from first user message or use "Untitled"
            title = self._get_conversation_title(conv)

            self.table.add_row(
                title,
                key=conv["session_id"],
            )
            self.loaded_count += 1

        self.conversation_count = self.loaded_count
        self._update_title()
        self._update_empty_state()

    async def reload_conversations(self) -> None:
        """Reload all conversations from database asynchronously to avoid blocking UI.

        Clears current list and reloads from the beginning.
        Useful when a new conversation is created.
        """
        self.table.clear()
        self.loaded_count = 0
        self._is_searching = False
        self._update_empty_state()  # Update after clearing
        await self.load_conversations()

    def _get_conversation_title(self, conv: dict) -> str:  # type: ignore[type-arg]
        """Get conversation title from metadata or generate from first message.

        Args:
            conv: Conversation dict with metadata

        Returns:
            Conversation title string, truncated if necessary
        """
        # Try to get title from metadata
        metadata = conv.get("metadata", {})
        title: str
        if metadata and "title" in metadata:
            title = str(metadata["title"])
        else:
            # Load first user message as title
            messages = self.db.load_conversation(conv["session_id"])
            found_title: str | None = None
            for msg in messages:
                if msg["role"] in ("user", "human"):
                    # Use first line of first user message
                    content = msg["content"]
                    found_title = content.split("\n")[0]
                    break

            title = found_title if found_title else "Untitled Conversation"

        # Truncate if too long
        if len(title) > 50:
            title = title[:47] + "..."

        return title

    def _update_title(self) -> None:
        """Update border title with count."""
        self.border_title = f"Conversations ({self.conversation_count})"

    def _update_empty_state(self) -> None:
        """Update visibility of empty state label based on conversation count."""
        try:
            empty_label = self.query_one("#empty-conversation-label")
            empty_label.display = self.table.row_count == 0
        except Exception:
            # Widget not mounted yet or not found
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle conversation selection.

        Args:
            event: Row selection event from DataTable
        """
        if event.row_key is not None:
            conversation_id = str(event.row_key.value)
            self.selected_id = conversation_id
            self.post_message(self.ConversationSelected(conversation_id))

    async def search(self, query: str) -> None:
        """Search conversations using FTS5.

        Clears current list and displays search results. Empty query
        reloads all conversations.

        Args:
            query: Search query string (FTS5 syntax supported)
        """
        if not query.strip():
            # Empty query - reload all conversations
            self.table.clear()
            self.loaded_count = 0
            self._is_searching = False
            await self.load_conversations()
            return

        # Mark as searching to prevent lazy load
        self._is_searching = True

        # FTS5 search in executor to avoid blocking
        import asyncio

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            self.db.search_conversations,
            query,
        )

        # Clear and populate with results
        self.table.clear()
        self.loaded_count = 0

        for conv in results:
            # Get title
            title = self._get_conversation_title(conv)

            self.table.add_row(
                title,
                key=conv["session_id"],
            )

        self.conversation_count = len(results)
        self._update_title()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlighting to trigger lazy load.

        Args:
            event: Row highlighting event from DataTable
        """
        # Don't lazy load during search
        if self._is_searching:
            return

        # Check if near bottom (within LAZY_LOAD_THRESHOLD rows)
        if event.cursor_row >= self.table.row_count - self.LAZY_LOAD_THRESHOLD:
            # Load next batch asynchronously
            self.run_worker(
                self.load_conversations(limit=self.INITIAL_LOAD), exclusive=True
            )

    async def action_rename_conversation(self) -> None:
        """Prompt to rename the currently selected conversation."""
        if self.table.cursor_row is None:
            return

        # Get current row
        row_key = self.table.get_row_at(self.table.cursor_row)[0]
        if row_key is None:
            return

        conversation_id = str(row_key)
        current_title = str(
            self.table.get_cell_at(Coordinate(self.table.cursor_row, 0))
        )

        # Prompt for new title using app's built-in input
        self.app.push_screen(
            RenameConversationModal(conversation_id, current_title, self.db),
            callback=self._handle_rename,
        )

    async def _handle_rename(self, result: tuple[str, str] | None) -> None:
        """Handle rename result from modal.

        Args:
            result: Tuple of (conversation_id, new_title) or None if cancelled
        """
        if result is None:
            return

        conversation_id, new_title = result

        # Update the table row
        for row_index, row_key in enumerate(self.table.rows.keys()):
            if str(row_key.value) == conversation_id:
                # Update row
                self.table.update_cell_at(Coordinate(row_index, 0), new_title)
                self._update_title()
                break


class RenameConversationModal(ModalScreen[tuple[str, str] | None]):
    """Modal for renaming a conversation."""

    DEFAULT_CSS = """
    RenameConversationModal {
        align: center middle;
    }

    RenameConversationModal > Container {
        width: 60;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1;
    }

    RenameConversationModal Label {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-style: bold;
        padding: 1;
    }

    RenameConversationModal Input {
        width: 100%;
        margin: 1 0;
    }

    RenameConversationModal .modal-actions {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
    }

    RenameConversationModal Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        conversation_id: str,
        current_title: str,
        db: ConversationDatabase,
    ) -> None:
        """Initialize rename modal.

        Args:
            conversation_id: ID of conversation to rename
            current_title: Current title of the conversation
            db: Database instance
        """
        super().__init__()
        self.conversation_id = conversation_id
        self.current_title = current_title
        self.db = db

    def compose(self) -> ComposeResult:
        """Compose modal widgets."""
        from textual.containers import Horizontal

        with Container():
            yield Label("Rename Conversation")
            self.input = Input(
                value=self.current_title,
                placeholder="Enter conversation title",
                id="title-input",
            )
            yield self.input
            with Horizontal(classes="modal-actions"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_mount(self) -> None:
        """Focus input on mount."""
        self.input.focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-button":
            new_title = self.input.value.strip()
            if new_title:
                # Update in database
                self.db.update_conversation_metadata(
                    self.conversation_id, {"title": new_title}
                )
                self.dismiss((self.conversation_id, new_title))
            else:
                self.dismiss(None)
        elif event.button.id == "cancel-button":
            self.dismiss(None)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        new_title = self.input.value.strip()
        if new_title:
            self.db.update_conversation_metadata(
                self.conversation_id, {"title": new_title}
            )
            self.dismiss((self.conversation_id, new_title))
        else:
            self.dismiss(None)
