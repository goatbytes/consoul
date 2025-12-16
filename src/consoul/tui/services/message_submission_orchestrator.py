"""Message submission orchestrator for Consoul TUI app.

This service orchestrates the complete message submission workflow including
validation, attachment processing, and coordination with streaming.
Extracted from app.py to reduce complexity (SOUL-270 Phase 9).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.tui.app import ConsoulApp
    from consoul.tui.widgets.input_area import InputArea

logger = logging.getLogger(__name__)


class MessageSubmissionOrchestrator:
    """Orchestrates user message submission workflow."""

    def __init__(self, app: ConsoulApp) -> None:
        """Initialize orchestrator.

        Args:
            app: The ConsoulApp instance
        """
        self.app = app

    async def handle_submission(self, event: InputArea.MessageSubmit) -> None:
        """Handle complete message submission workflow.

        Args:
            event: MessageSubmit event containing user's message content
        """
        from consoul.tui.widgets import MessageBubble

        user_message = event.content

        # Inject pending command output if available
        if self.app._pending_command_output:
            from consoul.tui.utils import inject_command_output

            command, output = self.app._pending_command_output
            user_message = inject_command_output(user_message, command, output)
            self.app.log.info(
                "[COMMAND_INJECT] Injected command output into user message"
            )
            # Clear buffer after injection
            self.app._pending_command_output = None

        # Check if AI model is available
        if self.app.chat_model is None or self.app.conversation is None:
            from consoul.tui.utils import create_model_not_initialized_error

            error_bubble = create_model_not_initialized_error()
            await self.app.chat_view.add_message(error_bubble)
            return

        # Reset tool call tracking for new user message
        self.app._tool_results = {}
        self.app._tool_call_iterations = 0
        if hasattr(self.app, "_last_tool_signature"):
            del self.app._last_tool_signature

        # Clear the "user scrolled away" flag when they submit a new message
        # This re-enables auto-scroll for the new conversation turn
        # IMPORTANT: Clear this BEFORE adding the message so add_message() will scroll
        self.app.chat_view._user_scrolled_away = False

        # Add user message to chat view FIRST for immediate visual feedback
        user_bubble = MessageBubble(user_message, role="user", show_metadata=True)
        await self.app.chat_view.add_message(user_bubble)

        # Show typing indicator immediately
        await self.app.chat_view.show_typing_indicator()

        # Track if this is the first message (conversation not yet in DB)
        is_first_message = (
            self.app.conversation.persist
            and not self.app.conversation._conversation_created
        )
        logger.debug(
            f"[MESSAGE_SUBMIT] is_first_message={is_first_message}, "
            f"persist={self.app.conversation.persist}, "
            f"_conversation_created={self.app.conversation._conversation_created}, "
            f"session_id={self.app.conversation.session_id}, "
            f"message_count={len(self.app.conversation.messages)}"
        )

        # Get attached files from InputArea
        from consoul.tui.widgets.input_area import InputArea

        input_area = self.app.query_one(InputArea)
        attached_files = input_area.attached_files.copy()

        # Process attachments using utility functions
        from consoul.tui.utils import (
            process_image_attachments,
            process_text_attachments,
        )

        # Process text file attachments - prepend to message
        final_message = process_text_attachments(attached_files, user_message)

        # Process image attachments - combine attached + auto-detected
        all_image_paths = process_image_attachments(
            attached_files, user_message, self.app.consoul_config
        )

        # Check if model supports vision
        model_supports_vision = self.app._model_supports_vision()
        logger.info(f"[IMAGE_DETECTION] Model supports vision: {model_supports_vision}")

        # Log multimodal condition check
        logger.info(
            f"[IMAGE_DETECTION] Condition check: "
            f"image_paths={bool(all_image_paths)}, model_supports_vision={model_supports_vision}, "
            f"combined={bool(all_image_paths) and model_supports_vision}"
        )
        if all_image_paths and model_supports_vision:
            logger.info(
                f"[IMAGE_DETECTION] Passing {len(all_image_paths)} image(s) to ConversationService"
            )

        # Clear attached files after processing
        input_area.attached_files.clear()
        input_area._update_file_chips()

        # Move EVERYTHING to a background worker to keep UI responsive
        async def _process_and_stream() -> None:
            # Convert TUI AttachedFile to SDK Attachment format
            from consoul.tui.utils import convert_attachments_to_sdk

            sdk_attachments = (
                convert_attachments_to_sdk(attached_files) if attached_files else None
            )

            # Start streaming AI response via ConversationService
            await self.app._stream_via_conversation_service(
                content=final_message,
                attachments=sdk_attachments,
            )

            # Sync conversation_id after streaming (in case it was created/updated by service)
            if self.app.conversation and self.app.conversation.session_id:
                self.app.conversation_id = self.app.conversation.session_id

            # Add new conversation to list if first message
            if (
                is_first_message
                and hasattr(self.app, "conversation_list")
                and self.app.conversation_id
            ):
                await self.app.conversation_list.prepend_conversation(
                    self.app.conversation_id
                )
                self.app._update_top_bar_state()

            # Persist attachments after streaming completes
            from consoul.tui.utils import handle_attachment_persistence

            await handle_attachment_persistence(
                self.app.conversation,
                attached_files,
                self.app._executor,
            )

        # Fire off all processing in background worker
        self.app.run_worker(_process_and_stream(), exclusive=False)
