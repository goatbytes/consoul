"""Streaming orchestrator for Consoul TUI app.

This service orchestrates AI response streaming including widget management,
tool approval integration, and title generation.
Extracted from app.py to reduce complexity (SOUL-270 Phase 9).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from consoul.tui.utils.streaming_widget_manager import StreamingWidgetManager

if TYPE_CHECKING:
    from consoul.sdk.models import Attachment
    from consoul.sdk.services.conversation import ConversationService
    from consoul.tui.app import ConsoulApp
    from consoul.tui.widgets.chat_view import ChatView

logger = logging.getLogger(__name__)


class StreamingOrchestrator:
    """Orchestrates AI response streaming workflow."""

    def __init__(
        self,
        conversation_service: ConversationService,
        chat_view: ChatView,
        app: ConsoulApp,
    ) -> None:
        """Initialize orchestrator.

        Args:
            conversation_service: Service for AI conversation
            chat_view: Chat view widget for message display
            app: The ConsoulApp instance (for callbacks and state)
        """
        self.conversation_service = conversation_service
        self.chat_view = chat_view
        self.app = app

    async def stream_message(
        self, content: str, attachments: list[Attachment] | None = None
    ) -> None:
        """Stream AI response for a user message.

        Args:
            content: User message content
            attachments: Optional list of file attachments
        """
        from consoul.tui.app import TUIToolApprover

        # Update streaming state
        self.app.streaming = True
        self.app._update_top_bar_state()

        # Create streaming widget manager
        stream_manager = StreamingWidgetManager(self.chat_view)

        # Begin timing BEFORE API request to accurately measure time-to-first-token
        stream_manager.begin_timing()

        # Store content for potential retry
        user_message = content

        try:
            # Create tool approver for this conversation
            tool_approver = TUIToolApprover(self.app)

            # Track first token to initialize stream widget
            first_token = True

            async for token in self.conversation_service.send_message(
                content,
                attachments=attachments,
                on_tool_request=tool_approver.on_tool_request,
            ):
                # On first token, create and show stream widget
                if first_token:
                    stream_widget = await stream_manager.start_streaming()
                    self.app._current_stream = stream_widget
                    first_token = False

                # Check for cancellation
                if self.app._stream_cancelled:
                    await stream_manager.cancel_stream()
                    return

                # Add token to stream
                await stream_manager.add_token(token.content, token.cost)

            # Finalize stream if we got any tokens
            if stream_manager.stream_widget:
                final_bubble = await stream_manager.finalize_stream(
                    self.conversation_service
                )

                # Generate title if this is the first exchange
                if final_bubble:
                    await self._handle_title_generation(stream_manager)
            else:
                # No tokens received - show error
                await stream_manager.show_no_response_error()

        except Exception as e:
            logger.error(f"Error streaming via ConversationService: {e}", exc_info=True)

            # Check if this is a "model does not support tools" error from Ollama
            error_msg = str(e).lower()
            if "does not support tools" in error_msg and "400" in error_msg:
                logger.warning(
                    f"Model {self.app.current_model} rejected tool calls. "
                    "Retrying without tools..."
                )

                # Remove tool binding by reinitializing model
                await self._retry_without_tools(stream_manager, user_message)
                return

            # Handle other errors normally
            await stream_manager.handle_stream_error(e)

    async def _retry_without_tools(
        self, stream_manager: StreamingWidgetManager, user_message: str
    ) -> None:
        """Retry streaming after removing tool binding from model.

        This handles the case where an Ollama model accepts bind_tools()
        but rejects tool usage at runtime with a 400 error.

        Args:
            stream_manager: Stream manager to clean up and restart
            user_message: Original user message to retry
        """
        # Remove the failed stream widget if it exists
        if stream_manager.stream_widget:
            await stream_manager.stream_widget.remove()

        # Reinitialize model WITHOUT tools by creating fresh ModelService
        # This automatically skips tool binding if model doesn't support it
        from consoul.sdk.services import ModelService

        # Create new ModelService without tool_service to skip tool binding
        if self.app.consoul_config:
            self.app.model_service = ModelService.from_config(
                self.app.consoul_config,  # type: ignore[arg-type]
                tool_service=None,
            )
            self.app.chat_model = self.app.model_service.get_model()

            # Update ConversationService model reference
            if self.conversation_service:
                self.conversation_service.model = self.app.chat_model

            # Update Conversation model reference
            if self.app.conversation:
                self.app.conversation._model = self.app.chat_model

        # Show notification to user
        self.app.notify(
            f"Model {self.app.current_model} doesn't support tools. Retrying...",
            severity="warning",
            timeout=3,
        )

        # Retry streaming by calling stream_message again
        # The conversation already has the user message, so we pass the same content
        await self.stream_message(user_message)

    async def _handle_title_generation(
        self, stream_manager: StreamingWidgetManager
    ) -> None:
        """Handle title generation after successful streaming.

        Args:
            stream_manager: Widget manager containing collected content
        """
        should_generate = self.app._should_generate_title()
        if self.app.title_generator and self.app.conversation and should_generate:
            # Get first user message (skip system messages)
            user_msg = None
            for msg in self.app.conversation.messages:
                if msg.type == "human":
                    user_msg = msg.content
                    break

            if user_msg and self.app.conversation.session_id:
                # Run title generation in background (non-blocking)
                self.app.run_worker(
                    self.app._generate_and_save_title(
                        self.app.conversation.session_id,
                        user_msg,  # type: ignore[arg-type]
                        "".join(stream_manager.collected_content),
                    ),
                    exclusive=False,
                    name=f"title_gen_{self.app.conversation.session_id}",
                )
            else:
                self.app.log.warning(
                    f"Cannot generate title: user_msg={bool(user_msg)}, "
                    f"session_id={self.app.conversation.session_id}"
                )
