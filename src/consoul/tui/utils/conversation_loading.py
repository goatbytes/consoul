"""Conversation loading and history reconstruction utilities.

This module provides utilities for loading conversations from the database
and reconstructing them in the chat view with proper UI elements.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

    from consoul.ai.database import ConversationDatabase
    from consoul.ai.history import ConversationHistory
    from consoul.config import ConsoulConfig
    from consoul.tui.widgets import ChatView

logger = logging.getLogger(__name__)


async def load_conversation_to_view(
    chat_view: ChatView,
    conversation_id: str,
    db: ConversationDatabase,
    theme: str,
    current_model: str,
    thinking_filter_callback: Any,
) -> None:
    """Load a conversation from the database and display it in the chat view.

    Args:
        chat_view: The ChatView widget to render messages to
        conversation_id: ID of the conversation to load
        db: Database instance to load conversation from
        theme: Theme for rendering messages
        current_model: Current model name for message reconstruction
        thinking_filter_callback: Callback to determine if thinking blocks should be shown

    Raises:
        Exception: If conversation loading fails
    """
    # Clear current chat view first
    await chat_view.clear_messages()

    # Show loading indicator
    await chat_view.show_loading_indicator()

    # Give the loading indicator time to render before we start loading messages
    await asyncio.sleep(0.1)

    try:
        # Load conversation from database with full metadata for UI reconstruction
        raw_messages = db.load_conversation_full(conversation_id)

        # Transform messages for display using ConversationDisplayService
        from consoul.sdk.services import ConversationDisplayService

        ui_messages = ConversationDisplayService.load_conversation_for_display(
            raw_messages, current_model=current_model
        )

        # Render messages in chat view
        from consoul.tui.utils import (
            display_reconstructed_attachments,
            render_ui_messages_to_chat,
        )

        await render_ui_messages_to_chat(
            chat_view,
            ui_messages,
            theme,
            thinking_filter_callback=thinking_filter_callback,
            attachment_display_callback=partial(
                display_reconstructed_attachments, chat_view
            ),
        )

        # Ensure we scroll to the bottom after loading all messages
        # Clear the "user scrolled away" flag first
        chat_view._user_scrolled_away = False
        # Use call_after_refresh to ensure all messages are laid out first
        chat_view.call_after_refresh(chat_view.scroll_end, animate=False)

        # Hide loading indicator and scroll to bottom
        try:
            # Hide loading indicator
            await chat_view.hide_loading_indicator()

            # Trigger scroll after layout completes
            chat_view.scroll_to_bottom_after_load()
        except Exception as scroll_err:
            logger.error(
                f"Error loading conversation scroll: {scroll_err}",
                exc_info=True,
            )
            raise

    except Exception:
        # Hide loading indicator on error
        await chat_view.hide_loading_indicator()
        raise


def reconstruct_conversation_history(
    config: ConsoulConfig,
    conversation_id: str,
    chat_model: BaseChatModel | None,
    conversation_config_getter: Any,
) -> ConversationHistory:
    """Reconstruct a ConversationHistory object for a loaded conversation.

    Args:
        config: Consoul configuration with model and profile settings
        conversation_id: ID of the conversation to reconstruct
        chat_model: Chat model instance to use (None will raise an error)
        conversation_config_getter: Callable that returns conversation config kwargs

    Returns:
        Reconstructed ConversationHistory instance

    Raises:
        ValueError: If chat_model is None
        Exception: If ConversationHistory creation fails
    """
    from consoul.ai import ConversationHistory

    if chat_model is None:
        raise ValueError("Chat model is not initialized")

    try:
        conv_kwargs = conversation_config_getter()
        conv_kwargs["session_id"] = conversation_id  # Resume this specific session
        return ConversationHistory(
            model_name=config.current_model,
            model=chat_model,
            **conv_kwargs,
        )
    except Exception as e:
        logger.error(
            f"[CONV_LOAD] Failed to create ConversationHistory: {e}",
            exc_info=True,
        )
        raise
