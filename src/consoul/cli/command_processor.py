"""Slash command processor for CLI chat sessions.

This module provides the CommandProcessor class for handling slash commands
in the CLI interface, enabling better separation of concerns and extensibility.

The CommandProcessor implements a simple command registry pattern where commands
are registered with names and optional aliases. Each command is a callable that
receives the ChatSession instance and any command arguments.

## Usage

The CommandProcessor is automatically initialized within ChatSession and handles
all slash commands through the `process()` method:

    >>> session = ChatSession(config)
    >>> session.process_command("/help")  # Delegates to CommandProcessor
    True

## Extending with Custom Commands

You can add custom commands to a ChatSession after initialization:

    ```python
    from consoul.cli import ChatSession

    # Create your command handler
    def my_custom_command(session: ChatSession, args: str) -> None:
        '''Handle custom command.'''
        session.console.print(f"[green]Custom command executed with: {args}[/green]")

    # Register the command
    session = ChatSession(config)
    session.command_processor.register_command(
        "mycmd",
        my_custom_command,
        aliases=["mc"]
    )

    # Now users can use /mycmd or /mc in the CLI
    >>> /mycmd test arguments
    Custom command executed with: test arguments
    ```

## Available Commands

The following commands are registered by default:

- **/help, /?** - Show available commands
- **/clear** - Clear conversation history
- **/tokens** - Show token usage statistics
- **/stats** - Show detailed session statistics
- **/exit, /quit** - Exit the chat session
- **/model <name>** - Switch to a different model
- **/tools <on|off>** - Enable or disable tool execution
- **/export <file>** - Export conversation to file

## Command Handler API

Command handlers must follow this signature:

    ```python
    def command_handler(session: ChatSession, args: str) -> None:
        '''Handle the command.

        Args:
            session: The ChatSession instance for state access
            args: Command arguments string (empty if no args)
        '''
        # Access session state
        session.console.print("Executing command...")
        session.conversation_service.conversation.messages

        # Perform command logic
        # Return None (commands print directly to console)
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from consoul.cli.chat_session import ChatSession


class CommandHandler(Protocol):
    """Protocol for command handler functions.

    Command handlers receive the ChatSession instance and any arguments,
    and perform the command action (typically printing to console and/or
    modifying session state).
    """

    def __call__(self, session: ChatSession, args: str) -> None:
        """Execute the command.

        Args:
            session: The ChatSession instance for state access
            args: Command arguments string (empty if no args)
        """
        ...


class CommandProcessor:
    """Processes slash commands for CLI chat sessions.

    Manages command registration, routing, and execution. Commands can
    be added dynamically via register_command(), making the system
    extensible for custom commands.

    Example:
        >>> processor = CommandProcessor(session)
        >>> processor.process("/help")  # Execute help command
        True
        >>> processor.process("regular input")  # Not a command
        False

        >>> # Register custom command
        >>> def custom_cmd(session, args):
        ...     session.console.print("Custom command executed!")
        >>> processor.register_command("custom", custom_cmd)
    """

    def __init__(self, session: ChatSession) -> None:
        """Initialize command processor.

        Args:
            session: ChatSession instance that commands will operate on
        """
        self.session = session
        self._commands: dict[str, CommandHandler] = {}
        self._aliases: dict[str, str] = {}
        self._register_default_commands()

    def process(self, cmd: str) -> bool:
        """Process slash command.

        Args:
            cmd: User input string to check for slash commands

        Returns:
            True if input was a command and was handled, False otherwise

        Example:
            >>> processor.process("/help")
            True
            >>> processor.process("regular message")
            False
        """
        # Not a command if doesn't start with /
        if not cmd.startswith("/"):
            return False

        # Parse command and arguments
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Resolve aliases
        command = self._aliases.get(command, command)

        # Execute command or show error
        if command in self._commands:
            self._commands[command](self.session, args)
        else:
            self.session.console.print(
                f"[red]Unknown command:[/red] /{command}\n"
                f"[dim]Type /help for available commands[/dim]"
            )

        return True

    def register_command(
        self,
        name: str,
        handler: CommandHandler,
        aliases: list[str] | None = None,
    ) -> None:
        """Register a new command handler.

        Args:
            name: Command name (without leading slash)
            handler: Command handler function
            aliases: Optional list of command aliases

        Example:
            >>> def my_command(session, args):
            ...     session.console.print(f"Executed with args: {args}")
            >>> processor.register_command("mycommand", my_command, aliases=["mc"])
            >>> processor.process("/mc test")  # Uses alias
            True
        """
        self._commands[name] = handler
        if aliases:
            for alias in aliases:
                self._aliases[alias] = name

    def list_commands(self) -> list[str]:
        """Get list of all registered command names.

        Returns:
            Sorted list of command names (without leading slash)
        """
        return sorted(self._commands.keys())

    def _register_default_commands(self) -> None:
        """Register default CLI commands.

        This is called during initialization to set up standard commands.
        """
        self.register_command("help", cmd_help, aliases=["?"])
        self.register_command("clear", cmd_clear)
        self.register_command("tokens", cmd_tokens)
        self.register_command("exit", cmd_exit, aliases=["quit"])
        self.register_command("model", cmd_model)
        self.register_command("tools", cmd_tools)
        self.register_command("export", cmd_export)
        self.register_command("stats", cmd_stats)


# ============================================================================
# Command Handlers
# ============================================================================


def cmd_help(session: ChatSession, args: str) -> None:
    """Show available slash commands."""
    from rich.table import Table

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

    session.console.print()
    session.console.print(table)
    session.console.print()


def cmd_clear(session: ChatSession, args: str) -> None:
    """Clear conversation history."""
    session.clear_history()
    session.console.print(
        "[green]✓[/green] Conversation history cleared (system prompt preserved)\n"
    )


def cmd_tokens(session: ChatSession, args: str) -> None:
    """Show token usage statistics."""
    from rich.panel import Panel

    from consoul.ai.context import get_model_token_limit

    stats = session.get_stats()

    # Get model token limit
    model_name = session.conversation_service.conversation.model_name
    max_tokens = get_model_token_limit(model_name)
    token_count = stats["token_count"]
    percentage = (token_count / max_tokens * 100) if max_tokens > 0 else 0

    session.console.print()
    session.console.print(
        Panel(
            f"[bold]Messages:[/bold] {stats['message_count']}\n"
            f"[bold]Tokens:[/bold] {token_count:,} / {max_tokens:,} ({percentage:.1f}%)\n"
            f"[bold]Model:[/bold] {model_name}",
            title="[bold cyan]Token Usage[/bold cyan]",
            border_style="cyan",
        )
    )
    session.console.print()


def cmd_exit(session: ChatSession, args: str) -> None:
    """Exit the chat session."""
    session._should_exit = True
    session.console.print("[dim]Exiting...[/dim]\n")


def cmd_model(session: ChatSession, args: str) -> None:
    """Switch to a different model."""
    import logging

    from consoul.ai.providers import get_chat_model, get_provider_from_model

    logger = logging.getLogger(__name__)

    if not args:
        session.console.print(
            "[red]Error:[/red] Model name required\n"
            "[dim]Usage: /model <model_name>[/dim]\n"
            "[dim]Example: /model gpt-4o[/dim]\n"
        )
        return

    model_name = args.strip()

    try:
        # Auto-detect provider from model name
        detected_provider = get_provider_from_model(model_name)

        if detected_provider:
            session.config.core.current_provider = detected_provider
            logger.info(
                f"Auto-detected provider: {detected_provider.value} for model: {model_name}"
            )

        # Update config
        session.config.core.current_model = model_name

        # Reinitialize model
        model_config = session.config.get_current_model_config()  # type: ignore[no-untyped-call]
        new_model = get_chat_model(model_config, config=session.config)

        # Bind tools if registry exists
        if session.conversation_service.tool_registry:
            new_model = session.conversation_service.tool_registry.bind_to_model(
                new_model
            )

        session.conversation_service.model = new_model

        # Update history model reference
        session.conversation_service.conversation.model_name = model_name
        session.conversation_service.conversation._model = new_model

        session.console.print(
            f"[green]✓[/green] Switched to model: [cyan]{session.config.current_provider.value}/{model_name}[/cyan]\n"
        )

    except Exception as e:
        session.console.print(f"[red]Error switching model:[/red] {e}\n")
        logger.error(f"Failed to switch model to {model_name}: {e}", exc_info=True)


def cmd_tools(session: ChatSession, args: str) -> None:
    """Enable or disable tool execution."""
    from consoul.ai.providers import get_chat_model

    if not args:
        # Show current status
        tool_registry = session.conversation_service.tool_registry
        status = "enabled" if tool_registry else "disabled"
        tool_count = len(tool_registry) if tool_registry else 0
        session.console.print(
            f"[bold]Tools:[/bold] {status} ({tool_count} tools available)\n"
            f"[dim]Usage: /tools <on|off>[/dim]\n"
        )
        return

    arg_lower = args.strip().lower()

    if arg_lower == "off":
        if not session.conversation_service.tool_registry:
            session.console.print("[yellow]Tools are already disabled[/yellow]\n")
        else:
            # Store reference for re-enabling
            if not hasattr(session, "_saved_tool_registry"):
                session._saved_tool_registry = (  # type: ignore[attr-defined]
                    session.conversation_service.tool_registry
                )

            session.conversation_service.tool_registry = None
            # Re-bind model without tools
            model_config = session.config.get_current_model_config()  # type: ignore[no-untyped-call]
            session.conversation_service.model = get_chat_model(
                model_config, config=session.config
            )

            session.console.print("[green]✓[/green] Tools disabled\n")

    elif arg_lower == "on":
        if session.conversation_service.tool_registry:
            session.console.print("[yellow]Tools are already enabled[/yellow]\n")
        else:
            # Restore saved registry if available
            if hasattr(session, "_saved_tool_registry"):
                saved_registry = session._saved_tool_registry
                session.conversation_service.tool_registry = saved_registry
                # Re-bind tools to model
                session.conversation_service.model = saved_registry.bind_to_model(
                    session.conversation_service.model
                )
                tool_count = len(saved_registry)
                session.console.print(
                    f"[green]✓[/green] Tools enabled ({tool_count} tools available)\n"
                )
            else:
                session.console.print(
                    "[red]Error:[/red] No tool registry available\n"
                    "[dim]Tools were not initialized at session start[/dim]\n"
                )
    else:
        session.console.print(
            f"[red]Error:[/red] Invalid argument '{args}'\n"
            f"[dim]Usage: /tools <on|off>[/dim]\n"
        )


def cmd_export(session: ChatSession, args: str) -> None:
    """Export conversation to file."""
    import logging

    logger = logging.getLogger(__name__)

    if not args:
        session.console.print(
            "[red]Error:[/red] Filename required\n"
            "[dim]Usage: /export <filename>[/dim]\n"
            "[dim]Supported formats: .md (markdown), .json[/dim]\n"
        )
        return

    filename = args.strip()

    try:
        session.export_conversation(filename)
    except Exception as e:
        session.console.print(f"[red]Error exporting conversation:[/red] {e}\n")
        logger.error(f"Failed to export to {filename}: {e}", exc_info=True)


def cmd_stats(session: ChatSession, args: str) -> None:
    """Show detailed session statistics."""
    from rich.panel import Panel

    from consoul.ai.context import get_model_token_limit

    stats = session.get_stats()

    # Get model info
    model_name = session.conversation_service.conversation.model_name
    max_tokens = get_model_token_limit(model_name)
    token_count = stats["token_count"]
    percentage = (token_count / max_tokens * 100) if max_tokens > 0 else 0

    # Count messages by type
    message_counts = {"user": 0, "assistant": 0, "system": 0, "tool": 0}
    for msg in session.conversation_service.conversation.messages:
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
    tool_registry = session.conversation_service.tool_registry
    tools_status = "enabled" if tool_registry else "disabled"
    tool_count = len(tool_registry) if tool_registry else 0

    stats_text = (
        f"[bold]Model:[/bold] {session.config.current_provider.value}/{model_name}\n"
        f"[bold]Session ID:[/bold] {session.conversation_service.conversation.session_id}\n\n"
        f"[bold]Messages:[/bold]\n"
        f"  User: {message_counts['user']}\n"
        f"  Assistant: {message_counts['assistant']}\n"
        f"  System: {message_counts['system']}\n"
        f"  Tool: {message_counts['tool']}\n"
        f"  Total: {sum(message_counts.values())}\n\n"
        f"[bold]Tokens:[/bold] {token_count:,} / {max_tokens:,} ({percentage:.1f}%)\n\n"
        f"[bold]Tools:[/bold] {tools_status} ({tool_count} available)"
    )

    session.console.print()
    session.console.print(
        Panel(
            stats_text,
            title="[bold cyan]Session Statistics[/bold cyan]",
            border_style="cyan",
        )
    )
    session.console.print()
