"""Attachment persistence utilities for TUI.

Provides helper functions for saving and loading file attachments to/from the
database, enabling conversation replay with full attachment context.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from consoul.ai import ConversationHistory
    from consoul.tui.widgets.chat_view import ChatView
    from consoul.tui.widgets.input_area import AttachedFile

logger = logging.getLogger(__name__)

__all__ = [
    "display_reconstructed_attachments",
    "persist_attachments",
]


async def persist_attachments(
    conversation: ConversationHistory,
    message_id: int,
    attached_files: list[AttachedFile],
    executor: Executor | None = None,
) -> None:
    """Persist attachments to the database for UI reconstruction.

    Args:
        conversation: Conversation history with database connection
        message_id: The database message ID to link attachments to
        attached_files: List of AttachedFile objects to persist
        executor: Optional thread pool executor for async database operations
    """
    if not conversation or not conversation._db:
        return

    try:
        import asyncio
        from functools import partial

        loop = asyncio.get_event_loop()
        for file in attached_files:
            if executor:
                await loop.run_in_executor(
                    executor,
                    partial(
                        conversation._db.save_attachment,
                        message_id=message_id,
                        file_path=file.path,
                        file_type=file.type,
                        mime_type=file.mime_type,
                        file_size=file.size,
                    ),
                )
            else:
                # Synchronous fallback
                conversation._db.save_attachment(
                    message_id=message_id,
                    file_path=file.path,
                    file_type=file.type,
                    mime_type=file.mime_type,
                    file_size=file.size,
                )
        logger.debug(
            f"Persisted {len(attached_files)} attachment(s) for message {message_id}"
        )
    except Exception as e:
        logger.warning(f"Failed to persist attachments: {e}")


async def display_reconstructed_attachments(
    chat_view: ChatView,
    attachments: list[dict[str, Any]],
) -> None:
    """Display attachments from a loaded conversation using FileChip widgets.

    Args:
        chat_view: Chat view to add attachment widgets to
        attachments: List of attachment dicts from database
    """
    if not attachments:
        return

    from textual.containers import Horizontal

    from consoul.tui.widgets.historical_file_chip import HistoricalFileChip

    # Create a container for the attachment chips
    container = Horizontal(classes="historical-attachments")

    for att in attachments:
        file_path = att.get("file_path", "")
        file_type = att.get("file_type", "unknown")
        file_size = att.get("file_size")

        chip = HistoricalFileChip(
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
        )
        container.compose_add_child(chip)

    await chat_view.add_message(container)
