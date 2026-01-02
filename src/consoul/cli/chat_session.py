"""CLI chat session management for stateful conversations.

This module provides the ChatSession class for managing CLI-based
interactive conversations with AI models, including message history,
streaming responses, and persistence.
"""

from __future__ import annotations

import logging
import signal
from datetime import datetime
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from consoul.ai.exceptions import StreamingError
from consoul.sdk.services.conversation import ConversationService

if TYPE_CHECKING:
    from consoul.cli.approval import CliToolApprovalProvider
    from consoul.formatters.base import ExportFormatter
    from consoul.tui.config import ConsoulTuiConfig

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
        >>> from consoul.config.loader import load_tui_config
        >>> config = load_tui_config()
        >>> with ChatSession(config) as session:
        ...     response = session.send("Hello!")
        ...     print(response)
    """

    def __init__(
        self,
        config: ConsoulTuiConfig,
        approval_provider: CliToolApprovalProvider | None = None,
        system_prompt_override: str | None = None,
        resume_session_id: str | None = None,
    ) -> None:
        """Initialize chat session from Consoul TUI configuration.

        Args:
            config: ConsoulTuiConfig instance with model, provider, and profile settings
            approval_provider: Optional approval provider for tool calls.
                If not provided, creates a default CliToolApprovalProvider.
            system_prompt_override: Optional system prompt to prepend to profile's base prompt
            resume_session_id: Optional session ID to resume existing conversation

        Raises:
            MissingAPIKeyError: If required API key is not configured
            MissingDependencyError: If provider package is not installed
            ProviderInitializationError: If model initialization fails
        """
        self.config = config
        self.console = Console()
        self._interrupted = False
        self._original_sigint_handler = None
        self._should_exit = False  # Flag for /exit command
        self.system_prompt_override = system_prompt_override
        self.resume_session_id = resume_session_id

        # Auto-create approval provider if not provided
        if not approval_provider:
            from consoul.cli.approval import CliToolApprovalProvider

            approval_provider = CliToolApprovalProvider(console=self.console)
            logger.debug("Created default CliToolApprovalProvider")

        self.approval_provider: CliToolApprovalProvider = approval_provider

        # Initialize command processor
        from consoul.cli.command_processor import CommandProcessor

        self.command_processor = CommandProcessor(self)

        # Initialize ConversationService
        logger.info(
            f"Initializing conversation service: {config.current_provider.value}/{config.current_model}"
        )
        self.conversation_service = ConversationService.from_config(
            config.core,
            approval_provider=self.approval_provider,
            session_id=resume_session_id,
        )

        # Override system prompt if provided
        profile = config.get_active_profile()
        if resume_session_id:
            # Resume existing conversation - messages loaded via session_id in from_config()
            logger.info(f"Resuming conversation: {resume_session_id}")
        elif profile.system_prompt or system_prompt_override:
            # Build complete system prompt with environment context
            system_prompt = self._build_system_prompt(profile, config)
            self.conversation_service.conversation.add_system_message(system_prompt)
            logger.debug(f"Added system prompt: {system_prompt[:50]}...")

    def _build_system_prompt(self, profile: Any, config: ConsoulTuiConfig) -> str:
        """Build complete system prompt with environment context and tool documentation.

        Delegates to ProfileManager.build_profile_system_prompt() for consistency.

        Args:
            profile: Active profile configuration
            config: Complete Consoul TUI configuration

        Returns:
            Complete system prompt with environment context and tool documentation
        """
        from consoul.tui.services.profile_manager import ProfileManager

        # Get tool registry from conversation service
        tool_registry = self.conversation_service.tool_registry

        # Build base prompt using ProfileManager
        base_prompt = ProfileManager.build_profile_system_prompt(
            profile, config, tool_registry=tool_registry
        )

        # Prepend system prompt override if provided
        if self.system_prompt_override:
            if base_prompt:
                base_prompt = f"{self.system_prompt_override}\n\n{base_prompt}"
            else:
                base_prompt = self.system_prompt_override
            logger.debug(
                f"Prepended system prompt override ({len(self.system_prompt_override)} chars)"
            )

        return base_prompt

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
            Complete AI response text (includes tool execution context if tools were called)

        Raises:
            KeyboardInterrupt: If user interrupts during streaming (Ctrl+C)
            Exception: For API errors, rate limits, or other failures
        """
        # Run the async implementation synchronously
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._send_async(message, stream, show_prefix, render_markdown)
        )

    async def _send_async(
        self,
        message: str,
        stream: bool,
        show_prefix: bool,
        render_markdown: bool,
    ) -> str:
        """Async implementation of send() with tool execution support.

        This internal method handles the actual message sending and tool execution.
        The public send() method wraps this in asyncio.run_until_complete() for
        backward compatibility.
        """
        try:
            # Create tool approval adapter
            async def on_tool_request(tool_request: Any) -> bool:
                """Adapter to connect CliToolApprovalProvider to ConversationService."""
                # Check if auto-approved or auto-denied
                if tool_request.name in self.approval_provider.always_approve:
                    self.console.print(
                        f"[dim]✓ Auto-approved '{tool_request.name}' (always approve)[/dim]"
                    )
                    return True
                elif tool_request.name in self.approval_provider.never_approve:
                    self.console.print(
                        f"[dim]✗ Auto-denied '{tool_request.name}' (never approve)[/dim]"
                    )
                    return False

                # Use the approval provider's request method
                if self.conversation_service.tool_registry:
                    approval_response = await self.conversation_service.tool_registry.request_tool_approval(
                        tool_name=tool_request.name,
                        arguments=tool_request.arguments,
                        tool_call_id=tool_request.id,
                    )
                    return approval_response.approved
                return True

            # Stream response from ConversationService
            response_parts = []

            if show_prefix:
                self.console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")

            async for token in self.conversation_service.send_message(
                message,
                on_tool_request=on_tool_request,
            ):
                response_parts.append(token.content)

                # Display token
                if stream:
                    self.console.print(token.content, end="", markup=False)

                # Display tool execution results if present in metadata
                if "tool_result" in token.metadata:
                    result = token.metadata["tool_result"]
                    tool_name = token.metadata.get("tool_name", "unknown")
                    success = token.metadata.get("tool_success", True)

                    if success:
                        self.console.print(
                            Panel(
                                f"[green]{result[:500]}{'...' if len(result) > 500 else ''}[/green]",
                                title=f"Tool Result: {tool_name}",
                                border_style="green",
                            )
                        )
                    else:
                        self.console.print(
                            Panel(
                                f"[red]{result}[/red]",
                                title=f"Tool Error: {tool_name}",
                                border_style="red",
                            )
                        )

            response_text = "".join(response_parts)

            # Render as markdown if requested and not already streamed
            if not stream and render_markdown:
                md = Markdown(response_text)
                self.console.print(md)
            elif not stream:
                self.console.print(response_text)
            else:
                self.console.print()  # Newline after streaming

            return response_text

        except StreamingError as e:
            # User interrupted during streaming (Ctrl+C) - not an error
            self.console.print("\n\n[yellow]Interrupted[/yellow]")
            logger.info("User interrupted during streaming")
            self._interrupted = True
            raise KeyboardInterrupt() from e

        except KeyboardInterrupt:
            # Direct keyboard interrupt (non-streaming path)
            self.console.print("\n\n[yellow]Interrupted[/yellow]")
            logger.info("User interrupted during response")
            self._interrupted = True
            raise

        except Exception as e:
            # Log and re-raise actual errors
            logger.error(f"Error during send: {e}", exc_info=True)
            self.console.print(f"\n[red]Error: {e}[/red]")
            raise

    def clear_history(self) -> None:
        """Clear conversation history (keeps system prompt)."""
        # Get system messages
        system_messages = [
            msg
            for msg in self.conversation_service.conversation.messages
            if msg.type == "system"
        ]

        # Clear all messages
        self.conversation_service.conversation.messages.clear()

        # Re-add system messages
        for msg in system_messages:
            self.conversation_service.conversation.messages.append(msg)

        logger.info("Cleared conversation history (preserved system prompt)")

    def get_stats(self) -> dict[str, int]:
        """Get conversation statistics.

        Returns:
            Dictionary with message_count (excluding system messages) and token_count
        """
        # Count only user and assistant messages, exclude system messages
        user_and_assistant_messages = [
            msg
            for msg in self.conversation_service.conversation.messages
            if msg.type in ("human", "ai")
        ]

        return {
            "message_count": len(user_and_assistant_messages),
            "token_count": self.conversation_service.conversation.count_tokens(),
        }

    @property
    def should_exit(self) -> bool:
        """Check if the session should exit.

        Returns:
            True if /exit or /quit command was issued
        """
        return self._should_exit

    def process_command(self, cmd: str) -> bool:
        """Process slash command.

        Delegates to CommandProcessor for actual command execution.

        Args:
            cmd: User input string to check for slash commands

        Returns:
            True if input was a command and was handled, False otherwise

        Example:
            >>> session.process_command("/help")
            True
            >>> session.process_command("regular message")
            False
        """
        return self.command_processor.process(cmd)

    def export_conversation(self, filepath: str) -> None:
        """Export conversation to file.

        Args:
            filepath: Path to output file. Format auto-detected from extension.
                     Supported: .md (markdown), .json

        Raises:
            ValueError: If file format is not supported
            IOError: If file cannot be written

        Example:
            >>> session.export_conversation("chat.md")
            >>> session.export_conversation("conversation.json")
        """
        from pathlib import Path

        from consoul.formatters.json_formatter import JSONFormatter
        from consoul.formatters.markdown import MarkdownFormatter

        output_path = Path(filepath)

        # Auto-detect format from extension
        extension = output_path.suffix.lower()

        formatter: ExportFormatter
        if extension == ".md":
            formatter = MarkdownFormatter()
        elif extension == ".json":
            formatter = JSONFormatter()
        else:
            raise ValueError(
                f"Unsupported format: {extension}. "
                "Supported formats: .md (markdown), .json"
            )

        # Build metadata
        conversation = self.conversation_service.conversation
        metadata = {
            "session_id": conversation.session_id,
            "model": conversation.model_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": len(conversation.messages),
        }

        # Convert messages to dict format
        from consoul.ai.history import to_dict_message

        messages = []
        for msg in conversation.messages:
            msg_dict = to_dict_message(msg)
            msg_dict["timestamp"] = datetime.now().isoformat()
            msg_dict["tokens"] = 0  # Could calculate per-message if needed
            messages.append(msg_dict)

        # Export using formatter
        formatter.export_to_file(metadata, messages, output_path)

        self.console.print(
            f"[green]✓[/green] Conversation exported to: [cyan]{filepath}[/cyan]\n"
        )

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
                    f"Session ended - conversation persisted (session_id: {self.conversation_service.conversation.session_id})"
                )
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
