"""TUI widgets module.

This package contains all Textual widgets for the Consoul TUI, including
chat views, input areas, message bubbles, and modal dialogs.
"""

from __future__ import annotations

from consoul.tui.widgets.chat_view import ChatView
from consoul.tui.widgets.contextual_top_bar import ContextualTopBar
from consoul.tui.widgets.conversation_list import ConversationList
from consoul.tui.widgets.input_area import InputArea
from consoul.tui.widgets.message_bubble import MessageBubble
from consoul.tui.widgets.model_picker_modal import ModelPickerModal
from consoul.tui.widgets.profile_selector_modal import ProfileSelectorModal
from consoul.tui.widgets.streaming_response import StreamingResponse

__all__ = [
    "ChatView",
    "ContextualTopBar",
    "ConversationList",
    "InputArea",
    "MessageBubble",
    "ModelPickerModal",
    "ProfileSelectorModal",
    "StreamingResponse",
]
