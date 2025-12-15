"""TUI widgets module.

This package contains all Textual widgets for the Consoul TUI, including
chat views, input areas, message bubbles, and modal dialogs.
"""

from __future__ import annotations

from consoul.tui.widgets.attachment_button import AttachmentButton
from consoul.tui.widgets.center_middle import CenterMiddle
from consoul.tui.widgets.chat_view import ChatView
from consoul.tui.widgets.command_output_bubble import CommandOutputBubble
from consoul.tui.widgets.contextual_top_bar import ContextualTopBar
from consoul.tui.widgets.conversation_list import ConversationList
from consoul.tui.widgets.enhanced_model_picker import EnhancedModelPicker
from consoul.tui.widgets.export_modal import ExportModal
from consoul.tui.widgets.file_attachment_modal import FileAttachmentModal
from consoul.tui.widgets.file_chip import FileChip
from consoul.tui.widgets.help_modal import HelpModal
from consoul.tui.widgets.historical_file_chip import HistoricalFileChip
from consoul.tui.widgets.import_modal import ImportModal
from consoul.tui.widgets.initialization_error_screen import InitializationErrorScreen
from consoul.tui.widgets.input_area import InputArea
from consoul.tui.widgets.local_model_card import LocalModelCard
from consoul.tui.widgets.message_bubble import MessageBubble
from consoul.tui.widgets.mlx_conversion_modal import MLXConversionModal
from consoul.tui.widgets.model_card import ModelCard
from consoul.tui.widgets.model_picker_modal import ModelPickerModal
from consoul.tui.widgets.permission_manager_screen import PermissionManagerScreen
from consoul.tui.widgets.profile_editor_modal import ProfileEditorModal
from consoul.tui.widgets.profile_selector_modal import ProfileSelectorModal
from consoul.tui.widgets.search_bar import SearchBar
from consoul.tui.widgets.send_button import SendButton
from consoul.tui.widgets.settings_screen import SettingsScreen
from consoul.tui.widgets.streaming_response import StreamingResponse
from consoul.tui.widgets.tool_approval_modal import ToolApprovalModal
from consoul.tui.widgets.tool_call_details_modal import ToolCallDetailsModal
from consoul.tui.widgets.tool_call_widget import ToolCallWidget
from consoul.tui.widgets.tool_formatter import format_tool_header
from consoul.tui.widgets.typing_indicator import TypingIndicator

__all__ = [
    "AttachmentButton",
    "CenterMiddle",
    "ChatView",
    "CommandOutputBubble",
    "ContextualTopBar",
    "ConversationList",
    "EnhancedModelPicker",
    "ExportModal",
    "FileAttachmentModal",
    "FileChip",
    "HelpModal",
    "HistoricalFileChip",
    "ImportModal",
    "InitializationErrorScreen",
    "InputArea",
    "LocalModelCard",
    "MLXConversionModal",
    "MessageBubble",
    "ModelCard",
    "ModelPickerModal",
    "PermissionManagerScreen",
    "ProfileEditorModal",
    "ProfileSelectorModal",
    "SearchBar",
    "SendButton",
    "SettingsScreen",
    "StreamingResponse",
    "ToolApprovalModal",
    "ToolCallDetailsModal",
    "ToolCallWidget",
    "TypingIndicator",
    "format_tool_header",
]
