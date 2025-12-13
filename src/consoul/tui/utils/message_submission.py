"""Message submission utilities for the TUI.

This module handles message preparation and attachment processing for
submitting user messages to the AI. It converts TUI attachment formats
to SDK formats and handles attachment persistence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from consoul.ai import ConversationHistory
    from consoul.tui.widgets.input_area import AttachedFile

import logging

logger = logging.getLogger(__name__)


def convert_attachments_to_sdk(
    attached_files: list[AttachedFile],
) -> list[Any]:
    """Convert TUI AttachedFile objects to SDK Attachment format.

    Filters out files with unsupported types ("unknown") to prevent ValueError
    in Attachment.__post_init__ which only accepts {"image","code","document","data"}.

    Args:
        attached_files: List of TUI AttachedFile objects with path, type, etc.

    Returns:
        List of SDK Attachment objects with path and type fields (unsupported types filtered)
    """
    from consoul.sdk.models import Attachment

    supported_types = {"image", "code", "document", "data"}
    sdk_attachments = []

    for f in attached_files:
        if f.type in supported_types:
            sdk_attachments.append(Attachment(path=f.path, type=f.type))
        else:
            logger.warning(
                f"Skipping attachment '{f.path}' with unsupported type '{f.type}'. "
                f"Supported types: {', '.join(supported_types)}"
            )

    return sdk_attachments


async def persist_message_attachments(
    conversation: ConversationHistory,
    user_message_id: int,
    attached_files: list[AttachedFile],
    executor: ThreadPoolExecutor,
) -> None:
    """Persist attachments to the database for a specific message.

    Args:
        conversation: Conversation instance with database connection
        user_message_id: ID of the user message to attach files to
        attached_files: List of attached files to persist
        executor: Thread pool executor for async file operations

    Raises:
        Exception: If attachment persistence fails
    """
    from consoul.tui.utils import persist_attachments

    logger.debug(
        f"Persisting {len(attached_files)} attachments to message {user_message_id}"
    )
    await persist_attachments(
        conversation,
        user_message_id,
        attached_files,
        executor,
    )
    logger.debug("Attachments persisted successfully")


async def get_user_message_id_from_conversation(
    conversation: ConversationHistory,
) -> int | None:
    """Get the most recent user message ID from conversation.

    Looks backwards through messages to find the last human message.

    Args:
        conversation: Conversation instance with database connection

    Returns:
        Message ID if found, None otherwise
    """
    if not conversation.persist or not conversation._db or not conversation.session_id:
        return None

    try:
        messages = conversation._db.load_conversation(conversation.session_id)
        # Find the last human message
        for msg in reversed(messages):
            if msg.get("role") == "user":
                msg_id = msg.get("id")
                return int(msg_id) if msg_id is not None else None
    except Exception as e:
        logger.error(f"Failed to get user message ID: {e}", exc_info=True)

    return None


async def handle_attachment_persistence(
    conversation: ConversationHistory | None,
    attached_files: list[AttachedFile],
    executor: ThreadPoolExecutor,
) -> None:
    """Handle complete attachment persistence workflow.

    Retrieves the user message ID and persists attachments if conditions are met.

    Args:
        conversation: Conversation instance (may be None)
        attached_files: List of files to persist
        executor: Thread pool executor for async operations
    """
    if not conversation or not attached_files:
        return

    user_message_id = await get_user_message_id_from_conversation(conversation)

    if user_message_id:
        try:
            await persist_message_attachments(
                conversation,
                user_message_id,
                attached_files,
                executor,
            )
        except Exception as e:
            logger.error(f"Failed to persist attachments: {e}", exc_info=True)
    else:
        logger.warning("Could not find user message ID for attachment persistence")
