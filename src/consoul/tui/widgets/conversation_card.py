"""ConversationCard - Individual conversation card widget for sidebar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Click

__all__ = ["ConversationCard"]


class ConversationCard(Vertical):
    """A beautiful card widget for displaying a single conversation.

    Displays the conversation title with support for multi-line text
    and visual feedback for selection state.
    """

    class CardClicked(Message):
        """Message sent when a card is clicked."""

        def __init__(self, conversation_id: str) -> None:
            """Initialize CardClicked message.

            Args:
                conversation_id: ID of the conversation that was clicked
            """
            super().__init__()
            self.conversation_id = conversation_id

    DEFAULT_CSS = """
    ConversationCard {
        width: 100%;
        height: auto;
        min-height: 5;
        padding: 1;
        margin: 0 1 1 0;  /* Add right margin for spacing from scrollbar */
        background: $surface;
        border-left: wide $primary;
    }

    ConversationCard:hover {
        background: $surface-lighten-1;
        border-left: wide $accent;
    }

    ConversationCard.selected {
        background: $primary;
        border-left: wide $secondary;
    }

    ConversationCard.selected:hover {
        background: $primary-lighten-1;
    }

    ConversationCard .card-title {
        width: 100%;
        color: $text;
        text-style: none;
    }

    ConversationCard.selected .card-title {
        color: auto;
        text-style: bold;
    }

    ConversationCard .card-date {
        width: 100%;
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }

    ConversationCard.selected .card-date {
        color: auto 70%;
    }
    """

    # Reactive properties
    is_selected: reactive[bool] = reactive(False)

    def __init__(
        self,
        conversation_id: str,
        title: str,
        date_str: str = "",
    ) -> None:
        """Initialize conversation card.

        Args:
            conversation_id: Unique ID for this conversation
            title: Conversation title (supports multi-line)
            date_str: Optional date string to display
        """
        super().__init__()
        self.conversation_id = conversation_id
        self.title_text = title
        self.date_str = date_str

    def compose(self) -> ComposeResult:
        """Compose the card widgets."""
        yield Label(self.title_text, classes="card-title")
        if self.date_str:
            yield Label(self.date_str, classes="card-date")

    def watch_is_selected(self, selected: bool) -> None:
        """Update visual state when selection changes."""
        self.set_class(selected, "selected")

    async def on_click(self, event: Click) -> None:
        """Handle click events on the card."""
        event.stop()
        # Post the CardClicked message
        self.post_message(self.CardClicked(self.conversation_id))

    def update_title(self, new_title: str) -> None:
        """Update the card title.

        Args:
            new_title: New title text
        """
        self.title_text = new_title
        title_label = self.query_one(".card-title", Label)
        title_label.update(new_title)
