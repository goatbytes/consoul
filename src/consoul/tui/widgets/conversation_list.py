"""ConversationList widget for displaying conversation history sidebar.

This module provides a virtualized conversation list using Textual's DataTable
with support for lazy loading and FTS5 full-text search for performance with
1000+ conversations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from consoul.tui.widgets.conversation_card import ConversationCard

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.ai.database import ConversationDatabase

__all__ = ["ConversationList", "DeleteConversationModal", "RenameConversationModal"]


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

    class ConversationDeleted(Message):
        """Message sent when a conversation is deleted.

        Attributes:
            conversation_id: The ID of the deleted conversation
            was_active: Whether this was the currently active conversation
        """

        def __init__(self, conversation_id: str, was_active: bool = False) -> None:
            """Initialize ConversationDeleted message.

            Args:
                conversation_id: The conversation ID that was deleted
                was_active: Whether this was the active conversation
            """
            super().__init__()
            self.conversation_id = conversation_id
            self.was_active = was_active

    # Reactive state
    conversation_count: reactive[int] = reactive(0)
    selected_id: reactive[str | None] = reactive(None)

    def watch_conversation_count(self, count: int) -> None:
        """Update top bar when conversation count changes."""
        try:
            from consoul.tui.widgets.contextual_top_bar import ContextualTopBar

            top_bar = self.app.query_one(ContextualTopBar)
            top_bar.conversation_count = count
        except Exception:
            pass  # Top bar might not be mounted yet

    # Key bindings
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+r", "rename_conversation", "Rename", show=True),
        Binding("ctrl+d", "delete_conversation", "Delete", show=True),
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
            VerticalScroll container with conversation cards and empty state label
        """
        # Empty state message (shown when no conversations exist)
        yield Vertical(
            Label("[dim i]No conversations yet[/]"),
            id="empty-conversation-label",
            classes="empty-state-content",
        )

        # Conversation cards container
        self.cards_container: VerticalScroll = VerticalScroll(id="cards-container")
        yield self.cards_container

    def on_mount(self) -> None:
        """Initialize conversation list on mount.

        Sets up styling and loads initial conversations.
        """
        self.border_title = "Conversations"
        self.add_class("conversation-list")

        # Show empty state initially (will be hidden if conversations are loaded)
        self._update_empty_state()

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

        # Add conversation cards
        # Safety check: ensure container exists
        if not hasattr(self, "cards_container") or self.cards_container is None:
            return

        # Get existing card IDs to avoid duplicates
        existing_ids = {
            card.conversation_id
            for card in self.cards_container.query(ConversationCard)
        }

        for conv in conversations:
            session_id = conv["session_id"]
            if session_id in existing_ids:
                continue

            # Get title from first user message or use "Untitled"
            title = self._get_conversation_title(conv)

            # Format date if available
            date_str = ""
            if "created_at" in conv:
                from datetime import datetime

                try:
                    dt = datetime.fromisoformat(conv["created_at"])
                    date_str = dt.strftime("%b %d, %Y")
                except (ValueError, TypeError):
                    pass

            # Create and mount card
            card = ConversationCard(
                conversation_id=session_id,
                title=title,
                date_str=date_str,
            )
            await self.cards_container.mount(card)
            self.loaded_count += 1

        self.conversation_count = self.loaded_count
        self._update_title()
        self._update_empty_state()

    async def prepend_conversation(self, conversation_id: str) -> None:
        """Add a single new conversation to the top of the list.

        More efficient than reload_conversations() when adding just one new conversation.
        Prevents the flicker caused by removing and re-adding all cards.

        Args:
            conversation_id: The session ID of the new conversation
        """
        # Check if conversation already exists in the list
        existing_cards = list(self.cards_container.query(ConversationCard))
        for i, card in enumerate(existing_cards):
            if card.conversation_id == conversation_id:
                # Card already exists
                if i == 0:
                    # Already at the top, nothing to do
                    return
                # Move to top by removing and re-adding at index 0
                await card.remove()
                await self.cards_container.mount(card, before=0)
                return

        # Fetch the conversation from database
        import asyncio

        loop = asyncio.get_event_loop()
        conversations = await loop.run_in_executor(
            None,
            self.db.list_conversations,
            1,  # Only fetch the newest one
            0,  # From the beginning
        )

        if not conversations or conversations[0]["session_id"] != conversation_id:
            # Conversation not found or not the newest
            # This can happen if user adds to an old conversation - that's OK!
            # Just silently return without reloading everything
            return

        conv = conversations[0]
        title = self._get_conversation_title(conv)

        # Format date if available
        date_str = ""
        if "created_at" in conv:
            from datetime import datetime

            try:
                dt = datetime.fromisoformat(conv["created_at"])
                date_str = dt.strftime("%b %d, %Y")
            except (ValueError, TypeError):
                pass

        # Create card
        card = ConversationCard(
            conversation_id=conversation_id,
            title=title,
            date_str=date_str,
        )

        # Mount at index 0 (top of list) instead of appending
        await self.cards_container.mount(card, before=0)
        self.loaded_count += 1
        self.conversation_count = self.loaded_count
        self._update_title()
        self._update_empty_state()

    async def reload_conversations(self) -> None:
        """Reload all conversations from database asynchronously to avoid blocking UI.

        Clears current list and reloads from the beginning.
        Useful when a new conversation is created.
        """
        # Remove all cards
        await self.cards_container.remove_children()
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
        is_empty = len(self.cards_container.query(ConversationCard)) == 0

        # Add/remove "empty" class which triggers CSS to show/hide empty state
        self.set_class(is_empty, "empty")

        # Hide cards container when empty to make room for empty state
        self.cards_container.display = not is_empty

    async def on_conversation_card_card_clicked(
        self,
        event: ConversationCard.CardClicked,
    ) -> None:
        """Handle conversation card selection.

        Args:
            event: Card click event from ConversationCard
        """
        conversation_id = event.conversation_id

        # Update selection state on all cards
        for card in self.cards_container.query(ConversationCard):
            card.is_selected = card.conversation_id == conversation_id

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
            await self.cards_container.remove_children()
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
        await self.cards_container.remove_children()
        self.loaded_count = 0

        for conv in results:
            # Get title and date
            title = self._get_conversation_title(conv)
            date_str = ""
            if "created_at" in conv:
                from datetime import datetime

                try:
                    dt = datetime.fromisoformat(conv["created_at"])
                    date_str = dt.strftime("%b %d, %Y")
                except (ValueError, TypeError):
                    pass

            # Create and mount card
            card = ConversationCard(
                conversation_id=conv["session_id"],
                title=title,
                date_str=date_str,
            )
            await self.cards_container.mount(card)

        self.conversation_count = len(results)
        self._update_title()
        self._update_empty_state()

    # Note: Lazy loading for cards can be implemented with scroll events
    # For now, we load all conversations initially for simplicity

    async def action_rename_conversation(self) -> None:
        """Prompt to rename the currently selected conversation."""
        if not self.selected_id:
            return

        # Find the selected card
        selected_card = None
        for card in self.cards_container.query(ConversationCard):
            if card.conversation_id == self.selected_id:
                selected_card = card
                break

        if not selected_card:
            return

        conversation_id = selected_card.conversation_id
        current_title = selected_card.title_text

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

        # Update the card title
        for card in self.cards_container.query(ConversationCard):
            if card.conversation_id == conversation_id:
                card.update_title(new_title)
                break

    async def action_delete_conversation(self) -> None:
        """Prompt to delete the currently selected conversation."""
        if not self.selected_id:
            return

        # Find the selected card
        selected_card = None
        for card in self.cards_container.query(ConversationCard):
            if card.conversation_id == self.selected_id:
                selected_card = card
                break

        if not selected_card:
            return

        conversation_id = selected_card.conversation_id
        conversation_title = selected_card.title_text

        # Show confirmation modal
        self.app.push_screen(
            DeleteConversationModal(conversation_id, conversation_title),
            callback=self._handle_delete,
        )

    async def _handle_delete(self, result: tuple[str, bool] | None) -> None:
        """Handle delete result from modal.

        Args:
            result: Tuple of (conversation_id, confirmed) or None if cancelled
        """
        if result is None or not result[1]:
            # Cancelled or not confirmed
            return

        conversation_id, _confirmed = result

        # Check if this is the currently active conversation
        was_active = conversation_id == self.selected_id

        try:
            # Delete from database
            self.db.delete_conversation(conversation_id)

            # Remove card from UI
            for card in self.cards_container.query(ConversationCard):
                if card.conversation_id == conversation_id:
                    # Remove the card
                    await card.remove()
                    self.conversation_count -= 1
                    self._update_title()
                    self._update_empty_state()

                    # Emit deletion message for ConsoulApp to handle
                    self.post_message(
                        self.ConversationDeleted(conversation_id, was_active)
                    )
                    break

        except Exception as e:
            # Show error notification
            self.app.notify(
                f"Failed to delete conversation: {e}",
                severity="error",
                timeout=5,
            )


class RenameConversationModal(ModalScreen[tuple[str, str] | None]):
    """Modal for renaming a conversation."""

    DEFAULT_CSS = """
    RenameConversationModal {
        align: center middle;
    }

    RenameConversationModal > Container {
        width: 80;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1;
    }

    RenameConversationModal Label {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }

    RenameConversationModal Input {
        width: 100%;
    }

    RenameConversationModal .modal-actions {
        width: 100%;
        height: auto;
        min-height: 6;
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


class DeleteConversationModal(ModalScreen[tuple[str, bool] | None]):
    """Modal for confirming conversation deletion."""

    DEFAULT_CSS = """
    DeleteConversationModal {
        align: center middle;
    }

    DeleteConversationModal > Container {
        width: 60;
        height: auto;
        background: $panel;
        border: thick $error;
        padding: 2;
    }

    DeleteConversationModal Label {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }

    DeleteConversationModal .warning-text {
        text-style: bold;
        color: $error;
    }

    DeleteConversationModal .modal-actions {
        width: 100%;
        height: auto;
        min-height: 6;
        layout: horizontal;
        align: center middle;
        margin-top: 1;
    }

    DeleteConversationModal Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        conversation_id: str,
        conversation_title: str,
    ) -> None:
        """Initialize delete confirmation modal.

        Args:
            conversation_id: ID of conversation to delete
            conversation_title: Title of the conversation for display
        """
        super().__init__()
        self.conversation_id = conversation_id
        self.conversation_title = conversation_title

    def compose(self) -> ComposeResult:
        """Compose modal widgets."""
        from textual.containers import Horizontal

        with Container():
            yield Label("Delete Conversation")
            yield Label(
                f"Are you sure you want to delete '{self.conversation_title}'?",
                classes="warning-text",
            )
            yield Label("[dim]This action cannot be undone.[/]")
            with Horizontal(classes="modal-actions"):
                yield Button("Delete", variant="error", id="delete-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_mount(self) -> None:
        """Focus cancel button on mount for safety."""
        cancel_button = self.query_one("#cancel-button", Button)
        cancel_button.focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "delete-button":
            self.dismiss((self.conversation_id, True))
        elif event.button.id == "cancel-button":
            self.dismiss((self.conversation_id, False))
