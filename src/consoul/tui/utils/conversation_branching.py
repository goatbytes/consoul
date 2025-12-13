"""Conversation branching utilities.

This module provides utilities for creating and managing conversation branches.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.ai.database import ConversationDatabase

logger = logging.getLogger(__name__)


async def create_conversation_branch(
    db: ConversationDatabase,
    source_conversation_id: str,
    branch_message_id: int,
    new_model: str | None = None,
) -> str:
    """Create a new conversation branch from an existing conversation.

    Creates a new conversation containing all messages up to and including
    the specified message ID. This allows exploring different conversation
    paths from any point.

    Args:
        db: Database instance to perform the branch operation
        source_conversation_id: Source conversation session ID
        branch_message_id: Message ID to branch from (inclusive)
        new_model: Optional model for the new conversation (defaults to source model)

    Returns:
        Session ID of the newly created branched conversation

    Raises:
        Exception: If conversation branching fails

    Example:
        >>> new_session = await create_conversation_branch(
        ...     db, "session-123", message_id=5
        ... )
        >>> # New conversation now contains messages 1-5 from original
    """
    logger.info(
        f"Branching conversation {source_conversation_id} at message {branch_message_id}"
    )

    try:
        # Branch the conversation in the database
        new_session_id = db.branch_conversation(
            source_session_id=source_conversation_id,
            branch_at_message_id=branch_message_id,
            new_model=new_model,
        )

        logger.info(f"Created branched conversation: {new_session_id}")
        return new_session_id

    except Exception as e:
        logger.error(f"Failed to branch conversation: {e}")
        raise
