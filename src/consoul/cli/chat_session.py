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
from rich.table import Table

from consoul.ai import ConversationHistory, get_chat_model
from consoul.ai.exceptions import StreamingError
from consoul.ai.streaming import stream_response

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

    from consoul.ai.tools.registry import ToolRegistry
    from consoul.cli.approval import CliToolApprovalProvider
    from consoul.config import ConsoulConfig
    from consoul.formatters.base import ExportFormatter

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

    def __init__(
        self,
        config: ConsoulConfig,
        tool_registry: ToolRegistry | None = None,
        approval_provider: CliToolApprovalProvider | None = None,
        max_tool_iterations: int = 5,
    ) -> None:
        """Initialize chat session from Consoul configuration.

        Args:
            config: ConsoulConfig instance with model, provider, and settings
            tool_registry: Optional tool registry for tool execution support
            approval_provider: Optional approval provider for tool calls.
                If tool_registry is provided but approval_provider is not,
                creates a default CliToolApprovalProvider.
            max_tool_iterations: Maximum number of tool call iterations per message (default: 5)

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
        self.max_tool_iterations = max_tool_iterations

        # Tool execution support
        self.tool_registry = tool_registry
        if tool_registry and not approval_provider:
            # Auto-create approval provider if registry provided
            from consoul.cli.approval import CliToolApprovalProvider

            approval_provider = CliToolApprovalProvider(console=self.console)
            logger.debug("Created default CliToolApprovalProvider")

        self.approval_provider: CliToolApprovalProvider | None = approval_provider

        # Initialize chat model from config
        logger.info(
            f"Initializing chat model: {config.current_provider.value}/{config.current_model}"
        )
        model_config = config.get_current_model_config()
        self.model: BaseChatModel = get_chat_model(model_config, config=config)

        # Bind tools to model if registry provided
        if self.tool_registry:
            self.model = self.tool_registry.bind_to_model(self.model)
            logger.info(f"Bound {len(self.tool_registry)} tools to model")

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
            # Build complete system prompt with environment context
            system_prompt = self._build_system_prompt(profile, config)
            self.history.add_system_message(system_prompt)
            logger.debug(f"Added system prompt: {system_prompt[:50]}...")

    def _build_system_prompt(self, profile: Any, config: ConsoulConfig) -> str:
        """Build complete system prompt with environment context and tool documentation.

        Args:
            profile: Active profile configuration
            config: Complete Consoul configuration

        Returns:
            Complete system prompt with environment context and tool documentation
        """
        from consoul.ai.environment import get_environment_context
        from consoul.ai.prompt_builder import build_system_prompt

        # Start with base system prompt
        base_prompt = profile.system_prompt

        # Inject environment context if enabled
        include_system = (
            profile.context.include_system_info if hasattr(profile, "context") else True
        )
        include_git = (
            profile.context.include_git_info if hasattr(profile, "context") else True
        )

        if include_system or include_git:
            env_context = get_environment_context(
                include_system_info=include_system,
                include_git_info=include_git,
            )
            if env_context:
                # Prepend environment context to system prompt
                base_prompt = f"{env_context}\n\n{base_prompt}"
                logger.debug(f"Injected environment context ({len(env_context)} chars)")

        # Build final system prompt with tool documentation
        system_prompt = build_system_prompt(base_prompt, self.tool_registry)

        return system_prompt or base_prompt

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
        # Add user message to history
        self.history.add_user_message(message)
        logger.debug(f"Added user message: {message[:50]}...")

        # Get messages for API call (use BaseMessage objects, not dicts)
        messages = self.history.get_messages()

        # Tool execution loop (handles multi-step tool calls)
        tool_iteration = 0

        try:
            while tool_iteration < self.max_tool_iterations:
                if stream:
                    # Stream response token-by-token
                    response_text, ai_message = stream_response(
                        self.model,
                        messages,
                        console=self.console,
                        show_prefix=show_prefix,
                        show_spinner=True,
                        render_markdown=render_markdown,
                    )
                else:
                    # Non-streaming response
                    ai_message = self.model.invoke(messages)
                    response_text = str(ai_message.content)

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

                # Check for tool calls
                if not (hasattr(ai_message, "tool_calls") and ai_message.tool_calls):
                    # No tool calls - return response
                    return response_text

                # Tool calls detected
                if not self.tool_registry or not self.approval_provider:
                    # No tool support configured - warn and return
                    self.console.print(
                        "\n[yellow]⚠ AI requested tool execution but tools are not enabled[/yellow]"
                    )
                    return response_text

                tool_iteration += 1
                logger.info(
                    f"Processing {len(ai_message.tool_calls)} tool calls (iteration {tool_iteration}/{self.max_tool_iterations})"
                )

                # Process each tool call
                for tool_call in ai_message.tool_calls:
                    await self._execute_tool_call(dict(tool_call))
                    # Tool result already added to history in _execute_tool_call

                # Get updated messages for next iteration
                messages = self.history.get_messages()

                # Continue loop to get AI's response after tool execution

            # Max iterations reached
            self.console.print(
                f"\n[yellow]⚠ Maximum tool iterations ({self.max_tool_iterations}) reached[/yellow]"
            )
            return response_text

        except StreamingError as e:
            # User interrupted during streaming (Ctrl+C) - not an error
            self.console.print("\n\n[yellow]Interrupted[/yellow]")
            logger.info("User interrupted during streaming")
            self._interrupted = True
            # Add partial response to history if available
            if e.partial_response:
                self.history.add_assistant_message(e.partial_response)
                logger.debug(f"Saved partial response: {e.partial_response[:50]}...")
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

    async def _execute_tool_call(self, tool_call: dict[str, Any]) -> str:
        """Execute a single tool call with approval workflow.

        Args:
            tool_call: Tool call dict from AIMessage.tool_calls with keys:
                - name: Tool name
                - args: Tool arguments dict
                - id: Tool call ID

        Returns:
            Tool execution result (success message or error)
        """
        from langchain_core.messages import ToolMessage

        tool_name = str(tool_call["name"])
        tool_args: dict[str, Any] = dict(tool_call["args"])
        tool_call_id = str(tool_call.get("id", ""))

        logger.debug(f"Executing tool: {tool_name} with args: {tool_args}")

        try:
            # Check if auto-approved or auto-denied
            assert self.approval_provider is not None, "Approval provider is required"

            if tool_name in self.approval_provider.always_approve:
                approved = True
                self.console.print(
                    f"[dim]✓ Auto-approved '{tool_name}' (always approve)[/dim]"
                )
            elif tool_name in self.approval_provider.never_approve:
                approved = False
                self.console.print(
                    f"[dim]✗ Auto-denied '{tool_name}' (never approve)[/dim]"
                )
            else:
                # Request approval from provider
                assert self.tool_registry is not None, "Tool registry is required"
                approval_response = await self.tool_registry.request_tool_approval(
                    tool_name=tool_name,
                    arguments=tool_args,
                    tool_call_id=tool_call_id,
                )
                approved = approval_response.approved

            if not approved:
                # Tool denied - send denial message to AI
                result = "Tool execution denied by user"
                self.console.print(
                    Panel(
                        "[red]Execution denied by user[/red]",
                        title=f"Tool Result: {tool_name}",
                        border_style="red",
                    )
                )
            else:
                # Tool approved - execute it
                assert self.tool_registry is not None, "Tool registry is required"
                tool_metadata = self.tool_registry.get_tool(tool_name)
                result_obj = tool_metadata.tool.invoke(tool_args)
                result = str(result_obj)

                # Display result
                self.console.print(
                    Panel(
                        f"[green]{result[:500]}{'...' if len(result) > 500 else ''}[/green]",
                        title=f"Tool Result: {tool_name}",
                        border_style="green",
                    )
                )
                logger.debug(
                    f"Tool {tool_name} executed successfully: {result[:100]}..."
                )

        except Exception as e:
            # Tool execution failed
            result = f"Tool execution error: {e}"
            self.console.print(
                Panel(
                    f"[red]{result}[/red]",
                    title=f"Tool Error: {tool_name}",
                    border_style="red",
                )
            )
            logger.error(f"Tool {tool_name} execution failed: {e}", exc_info=True)

        # Add tool result to history
        tool_message = ToolMessage(content=result, tool_call_id=tool_call_id)
        self.history.messages.append(tool_message)
        logger.debug(f"Added tool message to history: {result[:50]}...")

        return result

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
            Dictionary with message_count (excluding system messages) and token_count
        """
        # Count only user and assistant messages, exclude system messages
        user_and_assistant_messages = [
            msg for msg in self.history.messages if msg.type in ("human", "ai")
        ]

        return {
            "message_count": len(user_and_assistant_messages),
            "token_count": self.history.count_tokens(),
        }

    def process_command(self, cmd: str) -> bool:
        """Process slash command.

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
        # Not a command if doesn't start with /
        if not cmd.startswith("/"):
            return False

        # Parse command and arguments
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Command routing table
        handlers = {
            "help": self._cmd_help,
            "?": self._cmd_help,  # Alias
            "clear": self._cmd_clear,
            "tokens": self._cmd_tokens,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,  # Alias
            "model": self._cmd_model,
            "tools": self._cmd_tools,
            "export": self._cmd_export,
            "stats": self._cmd_stats,
        }

        # Execute command or show error
        if command in handlers:
            handlers[command](args)
        else:
            self.console.print(
                f"[red]Unknown command:[/red] /{command}\n"
                f"[dim]Type /help for available commands[/dim]"
            )

        return True

    def _cmd_help(self, args: str) -> None:
        """Show available slash commands."""
        table = Table(
            title="Available Slash Commands",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Arguments", style="yellow")
        table.add_column("Description")

        commands = [
            ("/help", "", "Show this help message"),
            ("/clear", "", "Clear conversation history (keeps system prompt)"),
            ("/tokens", "", "Show token usage and message count"),
            ("/stats", "", "Show detailed session statistics"),
            ("/exit", "", "Exit the chat session"),
            ("/model", "<model_name>", "Switch to a different model"),
            (
                "/tools",
                "<on|off>",
                "Enable or disable tool execution",
            ),
            (
                "/export",
                "<filename>",
                "Export conversation to file (.md or .json)",
            ),
        ]

        for cmd, args_str, desc in commands:
            table.add_row(cmd, args_str, desc)

        self.console.print()
        self.console.print(table)
        self.console.print()

    def _cmd_clear(self, args: str) -> None:
        """Clear conversation history."""
        self.clear_history()
        self.console.print(
            "[green]✓[/green] Conversation history cleared (system prompt preserved)\n"
        )

    def _cmd_tokens(self, args: str) -> None:
        """Show token usage statistics."""
        stats = self.get_stats()

        # Get model token limit
        from consoul.ai.context import get_model_token_limit

        max_tokens = get_model_token_limit(self.history.model_name)
        token_count = stats["token_count"]
        percentage = (token_count / max_tokens * 100) if max_tokens > 0 else 0

        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Messages:[/bold] {stats['message_count']}\n"
                f"[bold]Tokens:[/bold] {token_count:,} / {max_tokens:,} ({percentage:.1f}%)\n"
                f"[bold]Model:[/bold] {self.history.model_name}",
                title="[bold cyan]Token Usage[/bold cyan]",
                border_style="cyan",
            )
        )
        self.console.print()

    def _cmd_exit(self, args: str) -> None:
        """Exit the chat session."""
        self._should_exit = True
        self.console.print("[dim]Exiting...[/dim]\n")

    def _cmd_model(self, args: str) -> None:
        """Switch to a different model."""
        if not args:
            self.console.print(
                "[red]Error:[/red] Model name required\n"
                "[dim]Usage: /model <model_name>[/dim]\n"
                "[dim]Example: /model gpt-4o[/dim]\n"
            )
            return

        model_name = args.strip()

        try:
            # Auto-detect provider from model name
            from consoul.ai.providers import get_provider_from_model

            detected_provider = get_provider_from_model(model_name)

            if detected_provider:
                self.config.current_provider = detected_provider
                logger.info(
                    f"Auto-detected provider: {detected_provider.value} for model: {model_name}"
                )

            # Update config
            self.config.current_model = model_name

            # Reinitialize model
            model_config = self.config.get_current_model_config()
            new_model = get_chat_model(model_config, config=self.config)

            # Bind tools if registry exists
            if self.tool_registry:
                new_model = self.tool_registry.bind_to_model(new_model)

            self.model = new_model

            # Update history model reference
            self.history.model_name = model_name
            self.history._model = new_model

            self.console.print(
                f"[green]✓[/green] Switched to model: [cyan]{self.config.current_provider.value}/{model_name}[/cyan]\n"
            )

        except Exception as e:
            self.console.print(f"[red]Error switching model:[/red] {e}\n")
            logger.error(f"Failed to switch model to {model_name}: {e}", exc_info=True)

    def _cmd_tools(self, args: str) -> None:
        """Enable or disable tool execution."""
        if not args:
            # Show current status
            status = "enabled" if self.tool_registry else "disabled"
            tool_count = len(self.tool_registry) if self.tool_registry else 0
            self.console.print(
                f"[bold]Tools:[/bold] {status} ({tool_count} tools available)\n"
                f"[dim]Usage: /tools <on|off>[/dim]\n"
            )
            return

        arg_lower = args.strip().lower()

        if arg_lower == "off":
            if not self.tool_registry:
                self.console.print("[yellow]Tools are already disabled[/yellow]\n")
            else:
                # Store reference for re-enabling
                if not hasattr(self, "_saved_tool_registry"):
                    self._saved_tool_registry = self.tool_registry

                self.tool_registry = None
                # Re-bind model without tools
                model_config = self.config.get_current_model_config()
                self.model = get_chat_model(model_config, config=self.config)

                self.console.print("[green]✓[/green] Tools disabled\n")

        elif arg_lower == "on":
            if self.tool_registry:
                self.console.print("[yellow]Tools are already enabled[/yellow]\n")
            else:
                # Restore saved registry if available
                if hasattr(self, "_saved_tool_registry"):
                    self.tool_registry = self._saved_tool_registry
                    # Re-bind tools to model
                    self.model = self.tool_registry.bind_to_model(self.model)
                    tool_count = len(self.tool_registry)
                    self.console.print(
                        f"[green]✓[/green] Tools enabled ({tool_count} tools available)\n"
                    )
                else:
                    self.console.print(
                        "[red]Error:[/red] No tool registry available\n"
                        "[dim]Tools were not initialized at session start[/dim]\n"
                    )
        else:
            self.console.print(
                f"[red]Error:[/red] Invalid argument '{args}'\n"
                f"[dim]Usage: /tools <on|off>[/dim]\n"
            )

    def _cmd_export(self, args: str) -> None:
        """Export conversation to file."""
        if not args:
            self.console.print(
                "[red]Error:[/red] Filename required\n"
                "[dim]Usage: /export <filename>[/dim]\n"
                "[dim]Supported formats: .md (markdown), .json[/dim]\n"
            )
            return

        filename = args.strip()

        try:
            self.export_conversation(filename)
        except Exception as e:
            self.console.print(f"[red]Error exporting conversation:[/red] {e}\n")
            logger.error(f"Failed to export to {filename}: {e}", exc_info=True)

    def _cmd_stats(self, args: str) -> None:
        """Show detailed session statistics."""
        stats = self.get_stats()

        # Get model info
        from consoul.ai.context import get_model_token_limit

        max_tokens = get_model_token_limit(self.history.model_name)
        token_count = stats["token_count"]
        percentage = (token_count / max_tokens * 100) if max_tokens > 0 else 0

        # Count messages by type
        message_counts = {"user": 0, "assistant": 0, "system": 0, "tool": 0}
        for msg in self.history.messages:
            msg_type = msg.type
            if msg_type == "human":
                message_counts["user"] += 1
            elif msg_type == "ai":
                message_counts["assistant"] += 1
            elif msg_type == "system":
                message_counts["system"] += 1
            elif msg_type == "tool":
                message_counts["tool"] += 1

        # Tool status
        tools_status = "enabled" if self.tool_registry else "disabled"
        tool_count = len(self.tool_registry) if self.tool_registry else 0

        stats_text = (
            f"[bold]Model:[/bold] {self.config.current_provider.value}/{self.history.model_name}\n"
            f"[bold]Session ID:[/bold] {self.history.session_id}\n\n"
            f"[bold]Messages:[/bold]\n"
            f"  User: {message_counts['user']}\n"
            f"  Assistant: {message_counts['assistant']}\n"
            f"  System: {message_counts['system']}\n"
            f"  Tool: {message_counts['tool']}\n"
            f"  Total: {sum(message_counts.values())}\n\n"
            f"[bold]Tokens:[/bold] {token_count:,} / {max_tokens:,} ({percentage:.1f}%)\n\n"
            f"[bold]Tools:[/bold] {tools_status} ({tool_count} available)"
        )

        self.console.print()
        self.console.print(
            Panel(
                stats_text,
                title="[bold cyan]Session Statistics[/bold cyan]",
                border_style="cyan",
            )
        )
        self.console.print()

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
        metadata = {
            "session_id": self.history.session_id,
            "model": self.history.model_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": len(self.history.messages),
        }

        # Convert messages to dict format
        from consoul.ai.history import to_dict_message

        messages = []
        for msg in self.history.messages:
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
                    f"Session ended - conversation persisted (session_id: {self.history.session_id})"
                )
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
