"""Message preparation utilities for TUI.

Provides helper functions for preparing messages, injecting command output,
and creating standard message bubbles.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.tui.widgets import MessageBubble

logger = logging.getLogger(__name__)

__all__ = [
    "create_error_bubble",
    "create_model_not_initialized_error",
    "inject_command_output",
]


def inject_command_output(
    user_message: str, command: str, output: str, log: logging.Logger | None = None
) -> str:
    """Inject command output into user message.

    Args:
        user_message: Original user message
        command: Command that was executed
        output: Command output
        log: Optional logger for logging injection

    Returns:
        Message with command output prepended in shell_command tags
    """
    prefix = f"""<shell_command>
Command: {command}
Output:
{output}
</shell_command>

"""
    if log:
        log.info("[COMMAND_INJECT] Injected command output into user message")
    return prefix + user_message


def create_error_bubble(message: str, show_metadata: bool = False) -> MessageBubble:
    """Create a standard error message bubble.

    Args:
        message: Error message to display
        show_metadata: Whether to show metadata (default: False)

    Returns:
        MessageBubble with error styling
    """
    from consoul.tui.widgets import MessageBubble

    return MessageBubble(message, role="error", show_metadata=show_metadata)


def create_model_not_initialized_error() -> MessageBubble:
    """Create a standard 'model not initialized' error bubble.

    Returns:
        MessageBubble with model initialization error message
    """
    message = (
        "AI model not initialized. Please check your configuration.\n\n"
        "Ensure you have:\n"
        "- A valid profile with model configuration\n"
        "- Required API keys set in environment or .env file\n"
        "- Provider packages installed (e.g., langchain-openai)"
    )
    return create_error_bubble(message)
