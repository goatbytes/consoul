"""Conversation configuration builder utility.

Handles building ConversationHistory constructor kwargs from profile configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.config.models import ProfileConfig
    from consoul.tui.config import ConsoulTuiConfig

import logging

logger = logging.getLogger(__name__)


def build_conversation_config(
    profile: ProfileConfig | None,
    consoul_config: ConsoulTuiConfig | None,
) -> dict[str, Any]:
    """Get ConversationHistory kwargs from profile configuration.

    Extracts all conversation settings from the profile and prepares them
    for passing to ConversationHistory constructor. Handles summary_model
    initialization if specified.

    Args:
        profile: Active profile configuration (may be None)
        consoul_config: Consoul TUI configuration for model initialization (may be None)

    Returns:
        Dictionary of kwargs for ConversationHistory constructor with keys:
        persist, db_path, summarize, summarize_threshold, keep_recent,
        summary_model, max_tokens

    Note:
        session_id should be added separately when resuming conversations.
    """
    from consoul.ai import get_chat_model

    kwargs: dict[str, Any] = {}

    if profile and hasattr(profile, "conversation"):
        conv_config = profile.conversation

        # Basic persistence settings
        kwargs["persist"] = conv_config.persist
        if conv_config.db_path:
            kwargs["db_path"] = conv_config.db_path

        # Summarization settings
        kwargs["summarize"] = conv_config.summarize
        kwargs["summarize_threshold"] = conv_config.summarize_threshold
        kwargs["keep_recent"] = conv_config.keep_recent

        # Summary model (needs to be initialized as ChatModel instance)
        if conv_config.summary_model and consoul_config:
            try:
                kwargs["summary_model"] = get_chat_model(
                    conv_config.summary_model, config=consoul_config
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize summary_model '{conv_config.summary_model}': {e}"
                )
                kwargs["summary_model"] = None
        else:
            kwargs["summary_model"] = None

        # Context settings - pass max_context_tokens from profile
        # Note: 0 or None in ConversationHistory means auto-size to 75% of model capacity
        if hasattr(profile, "context"):
            context_config = profile.context
            kwargs["max_tokens"] = context_config.max_context_tokens
    else:
        # Fallback to defaults if profile not available
        kwargs = {
            "persist": True,
            "summarize": False,
            "summarize_threshold": 20,
            "keep_recent": 10,
            "summary_model": None,
            "max_tokens": None,  # Auto-size
        }

    return kwargs
