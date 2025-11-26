"""Enhanced CLI input with history and styling using prompt_toolkit.

This module provides professional CLI input experience with:
- History navigation (up/down arrows)
- Persistent history across sessions
- Styled prompts with Consoul branding
- Graceful exit handling (Ctrl+D, exit commands)
- Multi-line support (optional)

Example:
    >>> from consoul.cli.input import get_user_input
    >>> while True:
    ...     user_input = get_user_input()
    ...     if user_input is None:  # User wants to exit
    ...         break
    ...     print(f"You said: {user_input}")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

if TYPE_CHECKING:
    from prompt_toolkit.history import History

logger = logging.getLogger(__name__)

# Consoul brand colors
_CONSOUL_STYLE = Style.from_dict(
    {
        "prompt": "#00d9ff bold",  # Consoul cyan
    }
)

# Exit commands that trigger session end
_EXIT_COMMANDS = frozenset(["exit", "quit", "/quit"])


def get_user_input(
    prompt_text: str = "You: ",
    history_file: Path | None = None,
    multiline: bool = False,
) -> str | None:
    """Get user input with history navigation and styled prompts.

    Provides a professional CLI input experience using prompt_toolkit with:
    - Persistent history (saved to file)
    - Up/Down arrow navigation through history
    - Styled prompt with Consoul branding
    - Graceful exit handling (Ctrl+D, Ctrl+C, exit commands)
    - Optional multi-line input (Alt+Enter for newline)

    Args:
        prompt_text: Text to display as prompt (default: "You: ")
        history_file: Path to history file, or None to use in-memory history.
                     Default location is ~/.consoul/chat_history if not specified.
        multiline: Enable multi-line input mode. If False, Enter submits.
                  If True, use Alt+Enter to submit.

    Returns:
        User input string, or None if user wants to exit (Ctrl+D, Ctrl+C,
        or exit command like 'exit', 'quit', '/quit').

    Raises:
        OSError: If history file cannot be created or written to.

    Example:
        >>> user_input = get_user_input("Ask me: ")
        >>> if user_input:
        ...     print(f"Processing: {user_input}")
        ... elif user_input is None:
        ...     print("User exited")
    """
    # Setup history
    history: History
    if history_file is not None:
        # Ensure parent directory exists
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history = FileHistory(str(history_file))
        logger.debug(f"Using history file: {history_file}")
    else:
        # Use default location
        default_history = Path.home() / ".consoul" / "chat_history"
        default_history.parent.mkdir(parents=True, exist_ok=True)
        history = FileHistory(str(default_history))
        logger.debug(f"Using default history: {default_history}")

    # Create styled prompt
    formatted_prompt = FormattedText([("class:prompt", prompt_text)])

    # Create prompt session (reusable across multiple prompt() calls)
    session: PromptSession[str] = PromptSession(
        message=formatted_prompt,
        style=_CONSOUL_STYLE,
        history=history,
        multiline=multiline,
    )

    try:
        # Get user input
        user_input: str = session.prompt()

        # Strip whitespace
        user_input = user_input.strip()

        # Check for exit commands
        if not user_input or user_input.lower() in _EXIT_COMMANDS:
            logger.debug(f"Exit command detected: {user_input or '(empty)'}")
            return None

        return user_input

    except (EOFError, KeyboardInterrupt):
        # User pressed Ctrl+D or Ctrl+C
        logger.debug("User interrupted input (EOF or Ctrl+C)")
        return None
