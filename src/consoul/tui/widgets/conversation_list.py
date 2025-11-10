"""ConversationList widget for displaying conversation history sidebar.

This module provides a virtualized conversation list using Textual's DataTable
with support for lazy loading and FTS5 full-text search for performance with
1000+ conversations.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.ai.database import ConversationDatabase

__all__ = ["ConversationList"]


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

    def compose(self) -> ComposeResult:
        """Compose conversation list widgets.

        Yields:
            DataTable widget for displaying conversations
        """
        self.table = DataTable(cursor_type="row", zebra_stripes=True)
        yield self.table

    def on_mount(self) -> None:
        """Initialize conversation list on mount.

        Sets up table columns, styling, and loads initial conversations.
        """
        self.border_title = "Conversations"
        self.add_class("conversation-list")

        # Setup table columns
        self.table.add_column("Title", key="title")
        self.table.add_column("Date", key="date", width=12)

        # Load initial conversations
        self.load_conversations()

    def load_conversations(self, limit: int | None = None) -> None:
        """Load conversations from database.

        Args:
            limit: Number of conversations to load (default: INITIAL_LOAD)
        """
        limit = limit or self.INITIAL_LOAD

        # Fetch from database
        conversations = self.db.list_conversations(
            limit=limit, offset=self.loaded_count
        )

        # Add rows to table
        for conv in conversations:
            # Get title from first user message or use "Untitled"
            title = self._get_conversation_title(conv)

            # Format date
            created_at = datetime.fromisoformat(conv["created_at"])
            date_str = created_at.strftime("%Y-%m-%d")

            self.table.add_row(
                title,
                date_str,
                key=conv["session_id"],
            )
            self.loaded_count += 1

        self.conversation_count = self.loaded_count
        self._update_title()

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
            self.load_conversations()
            return

        # Mark as searching to prevent lazy load
        self._is_searching = True

        # FTS5 search
        results = self.db.search_conversations(query)

        # Clear and populate with results
        self.table.clear()
        self.loaded_count = 0

        for conv in results:
            # Get title
            title = self._get_conversation_title(conv)

            # Format date
            created_at = datetime.fromisoformat(conv["created_at"])
            date_str = created_at.strftime("%Y-%m-%d")

            self.table.add_row(
                title,
                date_str,
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
            # Load next batch
            self.load_conversations(limit=self.INITIAL_LOAD)
