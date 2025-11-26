"""CLI chat session management for stateful conversations.

This module provides the ChatSession class for managing CLI-based
interactive conversations with AI models, including message history,
streaming responses, and persistence.
"""

from __future__ import annotations

import logging
import signal
from typing import TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown

from consoul.ai import ConversationHistory, get_chat_model
from consoul.ai.streaming import stream_response

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

    from consoul.config import ConsoulConfig

logger = logging.getLogger(__name__)


class ChatSession:
    """Stateful CLI chat session with conversation history and streaming.

    Manages a complete chat session including:
    - Chat model initialization from config
    - Conversation history with context retention
    - Streaming token-by-token responses
    - Graceful interrupt handling (Ctrl+C)
    - Optional persistence to SQLite

    Example:
        >>> from consoul.config import ConsoulConfig
        >>> config = ConsoulConfig.load()
        >>> with ChatSession(config) as session:
        ...     response = session.send("Hello!")
        ...     print(response)
    """

    def __init__(self, config: ConsoulConfig) -> None:
        """Initialize chat session from Consoul configuration.

        Args:
            config: ConsoulConfig instance with model, provider, and settings

        Raises:
            MissingAPIKeyError: If required API key is not configured
            MissingDependencyError: If provider package is not installed
            ProviderInitializationError: If model initialization fails
        """
        self.config = config
        self.console = Console()
        self._interrupted = False
        self._original_sigint_handler = None

        # Initialize chat model from config
        logger.info(
            f"Initializing chat model: {config.current_provider.value}/{config.current_model}"
        )
        model_config = config.get_current_model_config()
        self.model: BaseChatModel = get_chat_model(model_config, config=config)

        # Get active profile for settings
        profile = config.get_active_profile()

        # Initialize conversation history
        persist = (
            profile.conversation.persist
            if hasattr(profile, "conversation")
            else True  # Default to persistence
        )
        logger.info(f"Initializing conversation history (persist={persist})")
        self.history = ConversationHistory(
            model_name=config.current_model,
            model=self.model,
            persist=persist,
        )
        if profile.system_prompt:
            self.history.add_system_message(profile.system_prompt)
            logger.debug(f"Added system prompt: {profile.system_prompt[:50]}...")

    def send(
        self,
        message: str,
        stream: bool = True,
        show_prefix: bool = True,
        render_markdown: bool = True,
    ) -> str:
        """Send a message and get AI response.

        Args:
            message: User message text
            stream: Whether to stream response token-by-token (default: True)
            show_prefix: Whether to show "Assistant: " prefix (default: True)
            render_markdown: Whether to render response as markdown (default: True)

        Returns:
            Complete AI response text

        Raises:
            KeyboardInterrupt: If user interrupts during streaming (Ctrl+C)
            Exception: For API errors, rate limits, or other failures
        """
        # Add user message to history
        self.history.add_user_message(message)
        logger.debug(f"Added user message: {message[:50]}...")

        # Get messages for API call
        messages = self.history.get_messages_as_dicts()

        try:
            if stream:
                # Stream response token-by-token
                response_text = stream_response(
                    self.model,
                    messages,
                    console=self.console,
                    show_prefix=show_prefix,
                    show_spinner=True,
                    render_markdown=render_markdown,
                )
            else:
                # Non-streaming response
                response = self.model.invoke(messages)
                response_text = str(response.content)

                if render_markdown:
                    if show_prefix:
                        self.console.print("\n[bold cyan]Assistant:[/bold cyan]")
                    md = Markdown(response_text)
                    self.console.print(md)
                else:
                    if show_prefix:
                        self.console.print(
                            "\n[bold green]Assistant:[/bold green] ", end=""
                        )
                    self.console.print(response_text)

            # Add assistant response to history
            self.history.add_assistant_message(response_text)
            logger.debug(f"Added assistant response: {response_text[:50]}...")

            return response_text

        except KeyboardInterrupt:
            # Graceful interrupt handling
            self.console.print("\n\n[yellow]Interrupted[/yellow]")
            logger.info("User interrupted during response")
            self._interrupted = True
            raise

        except Exception as e:
            # Log and re-raise errors
            logger.error(f"Error during send: {e}", exc_info=True)
            self.console.print(f"\n[red]Error: {e}[/red]")
            raise

    def clear_history(self) -> None:
        """Clear conversation history (keeps system prompt)."""
        # Get system messages
        system_messages = [msg for msg in self.history.messages if msg.type == "system"]

        # Clear all messages
        self.history.messages.clear()

        # Re-add system messages
        for msg in system_messages:
            self.history.messages.append(msg)

        logger.info("Cleared conversation history (preserved system prompt)")

    def get_stats(self) -> dict[str, int]:
        """Get conversation statistics.

        Returns:
            Dictionary with message_count and token_count
        """
        return {
            "message_count": len(self.history),
            "token_count": self.history.count_tokens(),
        }

    def __enter__(self) -> ChatSession:
        """Context manager entry - setup interrupt handling."""
        # Store original SIGINT handler
        self._original_sigint_handler = signal.signal(  # type: ignore[assignment]
            signal.SIGINT, signal.SIG_DFL
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """Context manager exit - cleanup and save if needed."""
        # Restore original SIGINT handler
        if self._original_sigint_handler:
            signal.signal(signal.SIGINT, self._original_sigint_handler)

        # Persist conversation if configured
        profile = self.config.get_active_profile()
        persist = (
            profile.conversation.persist if hasattr(profile, "conversation") else True
        )
        if persist and not self._interrupted:
            try:
                # History auto-saves via ConversationHistory
                logger.info(
                    f"Session ended - conversation persisted (session_id: {self.history.session_id})"
                )
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
