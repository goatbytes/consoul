"""TUI widgets module.

This package contains all Textual widgets for the Consoul TUI, including
chat views, input areas, message bubbles, and modal dialogs.
"""

from __future__ import annotations

from consoul.tui.widgets.chat_view import ChatView
from consoul.tui.widgets.input_area import InputArea
from consoul.tui.widgets.message_bubble import MessageBubble
from consoul.tui.widgets.streaming_response import StreamingResponse

__all__ = ["ChatView", "InputArea", "MessageBubble", "StreamingResponse"]

# Additional widgets will be imported here as they are implemented in Phase 2
# from consoul.tui.widgets.conversation_list import ConversationList
