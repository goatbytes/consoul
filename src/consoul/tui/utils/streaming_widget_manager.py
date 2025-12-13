"""Streaming widget management utilities for the TUI.

This module provides centralized management of streaming response widgets,
handling their lifecycle from creation through token collection to finalization.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.tui.widgets import ChatView, MessageBubble, StreamingResponse

import logging

logger = logging.getLogger(__name__)


class StreamingWidgetManager:
    """Manages streaming response widget lifecycle and token collection.

    This class centralizes all streaming widget operations including:
    - Creating and mounting stream widgets
    - Collecting tokens and updating display
    - Finalizing streams and creating message bubbles
    - Handling stream errors and cleanup
    - Tracking timing metrics (tokens/sec, time to first token)
    """

    def __init__(self, chat_view: ChatView) -> None:
        """Initialize the streaming widget manager.

        Args:
            chat_view: ChatView widget to add streaming responses to
        """
        self.chat_view = chat_view
        self.stream_widget: StreamingResponse | None = None
        self.collected_content: list[str] = []
        self.total_cost: float = 0.0
        self.stream_start_time: float | None = None
        self.first_token_time: float | None = None
        self.token_count: int = 0

    def begin_timing(self) -> None:
        """Begin timing tracking before API request starts.

        Call this before starting the streaming API request to accurately
        measure time-to-first-token.
        """
        self.stream_start_time = time.time()
        self.first_token_time = None
        self.token_count = 0

    async def start_streaming(self) -> StreamingResponse:
        """Create and mount a new streaming response widget.

        This hides the typing indicator and shows the stream widget.
        Note: Call begin_timing() before the API request to track timing.

        Returns:
            The newly created StreamingResponse widget
        """
        from consoul.tui.widgets import StreamingResponse

        await self.chat_view.hide_typing_indicator()
        self.stream_widget = StreamingResponse(renderer="hybrid")
        await self.chat_view.add_message(self.stream_widget)
        self.collected_content = []
        self.total_cost = 0.0

        return self.stream_widget

    async def add_token(
        self, token_content: str, token_cost: float | None = None
    ) -> None:
        """Add a token to the streaming widget and update display.

        Tracks first token timing for performance metrics.

        Args:
            token_content: The token text to add
            token_cost: Optional cost of this token
        """
        if not self.stream_widget:
            logger.warning("Cannot add token: stream widget not initialized")
            return

        # Track first token timing
        if self.first_token_time is None and self.stream_start_time is not None:
            self.first_token_time = time.time()

        self.collected_content.append(token_content)
        self.token_count += 1

        if token_cost is not None:
            self.total_cost += token_cost

        await self.stream_widget.add_token(token_content)

    async def finalize_stream(
        self,
        conversation_service: Any = None,
    ) -> MessageBubble | None:
        """Finalize the stream and create a message bubble.

        This removes the stream widget and creates a final MessageBubble
        with the complete content and timing metadata.

        Args:
            conversation_service: Optional service to extract tool calls from

        Returns:
            The final MessageBubble, or None if stream was empty
        """
        from consoul.tui.widgets import MessageBubble

        if not self.stream_widget:
            logger.warning("Cannot finalize stream: stream widget not initialized")
            return None

        final_content = "".join(self.collected_content)
        logger.debug(f"[STREAM] Finalizing stream, content_length={len(final_content)}")

        # Calculate timing metrics
        tokens_per_second: float | None = None
        time_to_first_token: float | None = None

        if self.stream_start_time is not None and self.token_count > 0:
            # Calculate total streaming time
            total_time = time.time() - self.stream_start_time
            if total_time > 0:
                tokens_per_second = self.token_count / total_time

            # Calculate time to first token
            if self.first_token_time is not None:
                time_to_first_token = self.first_token_time - self.stream_start_time

        # Finalize and remove stream widget
        await self.stream_widget.finalize_stream()
        await self.stream_widget.remove()
        self.stream_widget = None

        if not final_content:
            return None

        # Extract tool call data from conversation for MessageBubble
        from consoul.tui.utils import extract_tool_calls_from_conversation

        tool_calls_list = None
        if conversation_service and conversation_service.conversation:
            tool_calls_list = extract_tool_calls_from_conversation(
                conversation_service.conversation
            )

        # Create MessageBubble with timing metadata
        final_bubble = MessageBubble(
            final_content,
            role="assistant",
            show_metadata=True,
            token_count=self.token_count if self.token_count > 0 else None,
            tokens_per_second=tokens_per_second,
            time_to_first_token=time_to_first_token,
            estimated_cost=self.total_cost if self.total_cost > 0 else None,
            tool_calls=tool_calls_list,
        )

        # Add final bubble to chat view
        await self.chat_view.add_message(final_bubble)

        return final_bubble

    async def handle_stream_error(self, error: Exception) -> None:
        """Handle streaming errors by showing error bubble.

        Args:
            error: The exception that occurred during streaming
        """
        from consoul.tui.utils import create_error_bubble

        logger.error(f"Error during streaming: {error}", exc_info=True)

        # Hide typing indicator if still showing
        await self.chat_view.hide_typing_indicator()

        # Remove stream widget if present
        if self.stream_widget:
            await self.stream_widget.remove()
            self.stream_widget = None

        # Show error bubble
        error_bubble = create_error_bubble(f"Error: {error!s}")
        await self.chat_view.add_message(error_bubble)

    async def cancel_stream(self) -> None:
        """Cancel the current stream and clean up.

        This removes the stream widget without creating a message bubble.
        Resets all timing tracking state.
        """
        if self.stream_widget:
            await self.stream_widget.remove()
            self.stream_widget = None
        self.collected_content = []
        self.total_cost = 0.0
        self.stream_start_time = None
        self.first_token_time = None
        self.token_count = 0

    async def show_no_response_error(self) -> None:
        """Show error when no tokens were received from the stream."""
        from consoul.tui.utils import create_error_bubble

        await self.chat_view.hide_typing_indicator()
        error_bubble = create_error_bubble("No response received from AI")
        await self.chat_view.add_message(error_bubble)
