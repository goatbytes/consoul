"""CLI entry point for Consoul."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import click
except ImportError:
    print(
        "Error: CLI dependencies not installed.\n"
        "Install with: pip install consoul[tui]",
        file=sys.stderr,
    )
    sys.exit(1)

from consoul.config.loader import load_config
from consoul.tui.profiles import get_builtin_profiles, get_profile_description


def validate_temperature(
    ctx: click.Context, param: click.Parameter, value: float | None
) -> float | None:
    """Validate temperature parameter is in range 0.0-2.0."""
    if value is None:
        return value
    if not 0.0 <= value <= 2.0:
        raise click.BadParameter("Temperature must be between 0.0 and 2.0")
    return value


def validate_max_tokens(
    ctx: click.Context, param: click.Parameter, value: int | None
) -> int | None:
    """Validate max_tokens parameter is positive."""
    if value is None:
        return value
    if value <= 0:
        raise click.BadParameter("Max tokens must be greater than 0")
    return value


def _read_system_prompt_file(file_path: str, max_size: int = 10_000) -> str:
    """Read system prompt from file with size limit.

    Args:
        file_path: Path to file containing system prompt
        max_size: Maximum file size in bytes (default: 10KB)

    Returns:
        File content as string (stripped of leading/trailing whitespace)

    Raises:
        ValueError: If file too large or cannot be read
    """
    path = Path(file_path).resolve()

    # Check file size
    file_size = path.stat().st_size
    if file_size > max_size:
        raise ValueError(
            f"System prompt file too large: {file_size:,} bytes "
            f"(max: {max_size:,} bytes)"
        )

    # Read file with UTF-8 encoding
    try:
        return path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError as e:
        raise ValueError(f"Cannot read system prompt file: not valid UTF-8: {e}") from e
    except Exception as e:
        raise ValueError(f"Cannot read system prompt file: {e}") from e


@click.group(invoke_without_command=True)
@click.option(
    "--profile",
    "-p",
    default="default",
    help="Configuration profile to use",
)
@click.option(
    "--list-profiles",
    is_flag=True,
    help="List all available profiles and exit",
)
@click.option(
    "--temperature",
    type=float,
    callback=validate_temperature,
    help="Override model temperature (0.0-2.0)",
)
@click.option(
    "--model",
    help="Override model name",
)
@click.option(
    "--max-tokens",
    type=int,
    callback=validate_max_tokens,
    help="Override maximum tokens to generate",
)
@click.pass_context
def cli(
    ctx: click.Context,
    profile: str,
    list_profiles: bool,
    temperature: float | None,
    model: str | None,
    max_tokens: int | None,
) -> None:
    """Consoul - AI-powered conversational CLI tool."""
    # Build CLI overrides BEFORE loading config
    cli_overrides: dict[str, Any] = {}
    if temperature is not None or model is not None or max_tokens is not None:
        from consoul.config.models import Provider

        # Determine provider from model name if specified
        if model is not None:
            provider_str: str
            if "gpt" in model.lower() or "o1" in model.lower():
                provider_str = Provider.OPENAI.value
            elif "claude" in model.lower():
                provider_str = Provider.ANTHROPIC.value
            elif "gemini" in model.lower():
                provider_str = Provider.GOOGLE.value
            else:
                provider_str = Provider.OLLAMA.value

            cli_overrides["current_provider"] = provider_str
            cli_overrides["current_model"] = model

        # Build provider config overrides
        provider_config_overrides: dict[str, Any] = {}
        if temperature is not None:
            provider_config_overrides["default_temperature"] = temperature
        if max_tokens is not None:
            provider_config_overrides["default_max_tokens"] = max_tokens

        # Apply provider config overrides if we have any
        if provider_config_overrides and model is not None:
            cli_overrides.setdefault("provider_configs", {})[provider_str] = (
                provider_config_overrides
            )

    # Load configuration with CLI overrides applied
    config = load_config(profile_name=profile, cli_overrides=cli_overrides)

    # Handle --list-profiles
    if list_profiles:
        click.echo("Available profiles:\n")
        builtin = set(get_builtin_profiles().keys())

        for profile_name in sorted(config.profiles.keys()):
            description = get_profile_description(profile_name, config)
            marker = " (built-in)" if profile_name in builtin else " (custom)"
            active = " [active]" if profile_name == config.active_profile else ""
            click.echo(f"  {profile_name}{marker}{active}")
            click.echo(f"    {description}")
        ctx.exit(0)

    # Store in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["cli_overrides"] = cli_overrides

    # If no subcommand, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option(
    "--model",
    "-m",
    help="Model to use (e.g., gpt-4o, claude-3-5-sonnet-20241022, llama3)",
)
@click.option(
    "--no-stream",
    is_flag=True,
    help="Disable streaming responses (show complete response at once)",
)
@click.option(
    "--no-markdown",
    is_flag=True,
    help="Disable markdown rendering (show plain text)",
)
@click.option(
    "--tools/--no-tools",
    default=None,
    help="Enable/disable tool execution (overrides config)",
)
@click.option(
    "--multiline",
    is_flag=True,
    help="Enable multi-line input mode (use Alt+Enter to submit)",
)
@click.option(
    "--file",
    "files",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Include text file or PDF content in first message (can be used multiple times)",
)
@click.option(
    "--glob",
    "globs",
    multiple=True,
    type=str,
    help="Include files matching glob pattern in first message (e.g., '*.py', 'src/**/*.ts')",
)
@click.option(
    "--stdin",
    is_flag=True,
    help="Read initial message from stdin (for piping command output)",
)
@click.option(
    "--system",
    "system_prompt",
    type=str,
    help="Override system prompt for this session",
)
@click.option(
    "--system-file",
    "system_prompt_file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Read system prompt from file (mutually exclusive with --system)",
)
@click.pass_context
def chat(
    ctx: click.Context,
    model: str | None,
    no_stream: bool,
    no_markdown: bool,
    tools: bool | None,
    multiline: bool,
    files: tuple[str, ...],
    globs: tuple[str, ...],
    stdin: bool,
    system_prompt: str | None,
    system_prompt_file: str | None,
) -> None:
    """Start an interactive chat session with streaming responses.

    Features:
    - Streaming token-by-token responses
    - Rich markdown rendering
    - Conversation history with context
    - History navigation (up/down arrows)
    - Tool execution with approval (if enabled)
    - Session persistence

    Controls:
    - Enter: Send message
    - Ctrl+C: Cancel current message
    - Ctrl+D or 'exit': Quit session
    - Up/Down: Navigate input history
    """
    import logging

    from rich.console import Console
    from rich.panel import Panel

    from consoul.cli import ChatSession, CliToolApprovalProvider, get_user_input

    logger = logging.getLogger(__name__)
    console = Console()
    config = ctx.obj["config"]
    active_profile = config.get_active_profile()

    # Validate mutually exclusive system prompt options
    if system_prompt and system_prompt_file:
        console.print(
            "[red]Error: --system and --system-file are mutually exclusive[/red]"
        )
        ctx.exit(1)

    # Read system prompt from file if provided
    if system_prompt_file:
        try:
            system_prompt = _read_system_prompt_file(system_prompt_file)
            logger.debug(
                f"Loaded system prompt from {system_prompt_file} ({len(system_prompt)} chars)"
            )
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            ctx.exit(1)

    # Override model if specified
    if model:
        from consoul.ai.providers import get_provider_from_model

        config.current_model = model
        # Auto-detect provider from model name
        detected_provider = get_provider_from_model(model)
        if detected_provider:
            config.current_provider = detected_provider
            logger.info(
                f"Model override: {model} (provider: {detected_provider.value})"
            )
        else:
            logger.warning(
                f"Could not detect provider for model '{model}', using current provider: {config.current_provider.value}"
            )

    # Display welcome panel
    console.print()
    tool_info = ""
    tools_enabled = (
        tools
        if tools is not None
        else (config.tools.enabled if hasattr(config, "tools") else False)
    )

    if tools_enabled:
        tool_info = "\nTools: enabled"

    welcome_text = (
        f"[bold]Profile:[/bold] {active_profile.name}\n"
        f"[bold]Model:[/bold] {config.current_provider.value}/{config.current_model}"
        f"{tool_info}\n\n"
        f"[dim]Type /help for commands | exit or Ctrl+C to quit | Escape clears input[/dim]"
    )

    console.print(
        Panel(
            welcome_text,
            title="[bold cyan]Consoul Chat[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    # Setup tool registry if tools enabled
    tool_registry = None
    approval_provider = None

    if tools_enabled:
        try:
            from consoul.ai.tools import ToolRegistry
            from consoul.ai.tools.catalog import get_all_tool_names, get_tool_by_name

            # Create approval provider first
            approval_provider = CliToolApprovalProvider(console=console)

            # Create registry with config settings
            tool_config = config.tools if hasattr(config, "tools") else None
            if tool_config:
                tool_registry = ToolRegistry(
                    config=tool_config,
                    approval_provider=approval_provider,
                )

                # Register available tools based on config filters
                # Respect allowed_tools (whitelist) and risk_filter
                allowed = tool_config.allowed_tools
                if allowed is not None:
                    # Explicit whitelist (may be empty list = no tools)
                    tools_to_register: list[str] = list(allowed)
                else:
                    # No whitelist - use all tools subject to risk filter
                    tools_to_register = get_all_tool_names()

                for tool_name in tools_to_register:
                    try:
                        result = get_tool_by_name(tool_name)
                        if result is None:
                            logger.warning(f"Tool {tool_name} not found in catalog")
                            continue

                        tool, risk_level, _ = result

                        # Apply risk filter if configured
                        if (
                            hasattr(tool_config, "risk_filter")
                            and tool_config.risk_filter
                        ):
                            from consoul.ai.tools import RiskLevel

                            # Map risk levels to numeric values for comparison
                            risk_order = {
                                RiskLevel.SAFE: 0,
                                RiskLevel.CAUTION: 1,
                                RiskLevel.DANGEROUS: 2,
                                RiskLevel.BLOCKED: 3,
                            }

                            max_risk = risk_order.get(tool_config.risk_filter, 0)
                            current_risk = risk_order.get(risk_level, 3)

                            if current_risk > max_risk:
                                logger.debug(
                                    f"Skipping {tool_name}: {risk_level.value} > {tool_config.risk_filter.value}"
                                )
                                continue

                        tool_registry.register(tool, risk_level=risk_level)
                    except Exception as e:
                        logger.warning(f"Could not register tool {tool_name}: {e}")

                logger.info(f"Registered {len(tool_registry)} tools")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not enable tools: {e}[/yellow]")
            tool_registry = None
            approval_provider = None

    # Create chat session (this may take a moment for model initialization)
    try:
        with console.status("[cyan]Initializing chat model...[/cyan]", spinner="dots"):
            session = ChatSession(
                config=config,
                approval_provider=approval_provider,
                system_prompt_override=system_prompt,
            )
    except Exception as e:
        console.print(f"[red]Error initializing chat session: {e}[/red]")
        logger.error(f"Failed to initialize ChatSession: {e}", exc_info=True)
        ctx.exit(1)

    # Read from stdin if flag is set (only for first message)
    initial_stdin: str | None = None
    if stdin:
        from consoul.cli.stdin_reader import read_stdin

        try:
            initial_stdin = read_stdin()
            if initial_stdin is None:
                console.print(
                    "[yellow]Warning: --stdin flag set but no data on stdin[/yellow]"
                )
            else:
                logger.debug(
                    f"Read {len(initial_stdin)} bytes from stdin for initial message"
                )
        except ValueError as e:
            console.print(f"[yellow]Warning: Could not read stdin: {e}[/yellow]")

    # Process file attachments (load once at start for first message)
    initial_file_context: str | None = None
    if files or globs:
        from consoul.cli.file_reader import (
            expand_glob_pattern,
            format_files_context,
        )

        try:
            # Collect all file paths
            all_files: list[Path] = []

            # Add explicitly specified files
            for file_path in files:
                all_files.append(Path(file_path).resolve())

            # Expand glob patterns
            for glob_pattern in globs:
                expanded = expand_glob_pattern(glob_pattern, max_files=50)
                all_files.extend(expanded)

            # Remove duplicates while preserving order
            seen = set()
            unique_files = []
            for f in all_files:
                if f not in seen:
                    seen.add(f)
                    unique_files.append(f)

            if not unique_files:
                console.print(
                    "[yellow]Warning: No files found matching patterns[/yellow]"
                )
            else:
                # Format file contents
                initial_file_context = format_files_context(
                    unique_files, max_total_size=500_000
                )
                console.print(
                    f"[dim]Loaded {len(unique_files)} file(s) for context[/dim]"
                )
                logger.info(f"Loaded {len(unique_files)} file(s)")

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            ctx.exit(1)
        except Exception as e:
            console.print(f"[red]Error reading files: {e}[/red]")
            ctx.exit(1)

    # Main chat loop
    first_iteration = True
    with session:
        while True:
            try:
                user_input: str | None

                # If we have stdin or file content on first iteration, use it
                if first_iteration and (initial_stdin or initial_file_context):
                    prompt_parts = []

                    # Build the context
                    if initial_file_context:
                        prompt_parts.append(initial_file_context)

                    if initial_stdin:
                        from consoul.cli.stdin_reader import format_stdin_message

                        # If we already have file context, just append stdin, don't wrap it
                        if initial_file_context:
                            prompt_parts.append(f"<stdin>\n{initial_stdin}\n</stdin>")
                        else:
                            # No file context, will use format_stdin_message below
                            pass

                    console.print("[dim]Context loaded. Enter your question:[/dim]")
                    question = get_user_input(
                        prompt_text="You: ",
                        multiline=multiline,
                    )

                    # Handle exit
                    if question is None:
                        break

                    # Use default question if empty
                    if not question.strip():
                        question = "Analyze this content"

                    # Build final message
                    if initial_file_context and initial_stdin:
                        # Both contexts: file + stdin + question
                        user_input = "\n\n".join(prompt_parts) + f"\n\n{question}"
                    elif initial_file_context:
                        # Only file context
                        user_input = f"{initial_file_context}\n\n{question}"
                    else:
                        # Only stdin context
                        from consoul.cli.stdin_reader import format_stdin_message

                        # Type assertion: initial_stdin is guaranteed to be str here
                        assert initial_stdin is not None
                        user_input = format_stdin_message(initial_stdin, question)

                    first_iteration = False
                else:
                    # Normal input flow
                    user_input = get_user_input(
                        prompt_text="You: ",
                        multiline=multiline,
                    )
                    first_iteration = False

                    # Handle exit (Ctrl+D or 'exit' command)
                    if user_input is None:
                        break

                # Skip empty input (re-prompt)
                if not user_input:
                    continue

                # Check for slash commands
                if session.process_command(user_input):
                    # Command was handled, check if exit was requested
                    if session.should_exit:
                        break
                    # Otherwise continue to next prompt
                    continue

                # Send message and get response
                response = session.send(
                    user_input,
                    stream=not no_stream,
                    render_markdown=not no_markdown,
                )

                logger.debug(f"Response received: {response[:100]}...")

            except KeyboardInterrupt:
                # Ctrl+C - exit gracefully
                console.print("\n[yellow]Cancelled[/yellow]")
                break

            except Exception as e:
                # API errors, rate limits, network issues
                console.print(f"\n[red]Error: {e}[/red]\n")
                logger.error(f"Chat error: {e}", exc_info=True)
                # Continue loop, don't exit on errors
                continue

        # Display session stats on exit
        console.print()
        stats = session.get_stats()

        stats_text = (
            f"[bold]Messages:[/bold] {stats['message_count']}\n"
            f"[bold]Tokens:[/bold] {stats['token_count']:,}"
        )

        # Check if session was persisted
        if (
            hasattr(active_profile, "conversation")
            and active_profile.conversation.persist
        ):
            stats_text += (
                f"\n\n[dim]Session saved (ID: {session.history.session_id})[/dim]"
            )

        console.print(
            Panel(
                stats_text,
                title="[bold cyan]Session Summary[/bold cyan]",
                border_style="cyan",
            )
        )

        console.print("\n[dim]Goodbye![/dim]\n")


@cli.command()
@click.argument("message", required=False)
@click.option(
    "-m",
    "--message",
    "message_opt",
    help="Message to send (alternative to positional arg)",
)
@click.option(
    "--model",
    help="Model to use (e.g., gpt-4o, claude-3-5-sonnet-20241022, llama3)",
)
@click.option(
    "--attach",
    multiple=True,
    type=click.Path(exists=True),
    help="Attach files (images for vision-capable models)",
)
@click.option(
    "--file",
    "files",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Include text file or PDF content in message (can be used multiple times)",
)
@click.option(
    "--glob",
    "globs",
    multiple=True,
    type=str,
    help="Include files matching glob pattern (e.g., '*.py', '**/*.pdf', 'src/**/*.ts')",
)
@click.option(
    "--tools/--no-tools",
    default=None,
    help="Enable/disable tool execution (overrides config)",
)
@click.option(
    "--no-markdown",
    is_flag=True,
    help="Disable markdown rendering (show plain text)",
)
@click.option(
    "--stream/--no-stream",
    default=True,
    help="Enable/disable streaming responses (default: stream)",
)
@click.option(
    "--show-tokens",
    is_flag=True,
    help="Show token usage statistics",
)
@click.option(
    "--show-cost",
    is_flag=True,
    help="Show cost estimate",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Save response to file",
)
@click.option(
    "--stdin",
    is_flag=True,
    help="Read input from stdin (for piping command output)",
)
@click.option(
    "--system",
    "system_prompt",
    type=str,
    help="Override system prompt for this query",
)
@click.option(
    "--system-file",
    "system_prompt_file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Read system prompt from file (mutually exclusive with --system)",
)
@click.pass_context
def ask(
    ctx: click.Context,
    message: str | None,
    message_opt: str | None,
    model: str | None,
    attach: tuple[str, ...],
    files: tuple[str, ...],
    globs: tuple[str, ...],
    tools: bool | None,
    no_markdown: bool,
    stream: bool,
    show_tokens: bool,
    show_cost: bool,
    output: str | None,
    stdin: bool,
    system_prompt: str | None,
    system_prompt_file: str | None,
) -> None:
    """Ask a single question and get a response (non-interactive).

    Provides a quick way to get AI responses without starting an interactive
    chat session. Ideal for scripting, automation, and one-off queries.

    Examples:

        \b
        # Simple question
        consoul ask "What is 2+2?"

        \b
        # Using -m flag
        consoul ask -m "Explain Python decorators"

        \b
        # With model override
        consoul ask "Translate to Spanish" --model gpt-4o

        \b
        # With tools enabled
        consoul ask "Find bug in utils.py" --tools

        \b
        # Analyze image
        consoul ask "What error is shown?" --attach screenshot.png

        \b
        # Show usage stats
        consoul ask "Quick question" --show-tokens --show-cost

        \b
        # Save response to file
        consoul ask "Generate report" --output report.txt

        \b
        # Pipe command output
        git diff | consoul ask --stdin "Review this diff"
        docker ps | consoul ask --stdin "Which containers are using most memory?"
    """
    import logging

    from rich.console import Console

    from consoul.cli import ChatSession, CliToolApprovalProvider

    logger = logging.getLogger(__name__)
    console = Console()
    config = ctx.obj["config"]

    # Validate mutually exclusive system prompt options
    if system_prompt and system_prompt_file:
        console.print(
            "[red]Error: --system and --system-file are mutually exclusive[/red]"
        )
        ctx.exit(1)

    # Read system prompt from file if provided
    if system_prompt_file:
        try:
            system_prompt = _read_system_prompt_file(system_prompt_file)
            logger.debug(
                f"Loaded system prompt from {system_prompt_file} ({len(system_prompt)} chars)"
            )
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            ctx.exit(1)

    # Handle message from either positional arg or -m flag
    msg = message or message_opt
    if not msg:
        console.print("[red]Error: Message required[/red]")
        console.print("\nUsage:")
        console.print("  consoul ask MESSAGE")
        console.print("  consoul ask -m MESSAGE")
        console.print("\nExamples:")
        console.print('  consoul ask "What is 2+2?"')
        console.print('  consoul ask -m "Explain Python decorators"')
        ctx.exit(1)

    # Type assertion: msg is guaranteed to be str here
    assert isinstance(msg, str)

    # Read from stdin if flag is set
    if stdin:
        from consoul.cli.stdin_reader import format_stdin_message, read_stdin

        try:
            stdin_content = read_stdin()
            if stdin_content is None:
                console.print("[red]Error: --stdin flag set but no data on stdin[/red]")
                console.print("\nUsage:")
                console.print('  echo "data" | consoul ask --stdin "question"')
                console.print('  command | consoul ask --stdin "analyze this"')
                console.print('  consoul ask --stdin "analyze" < file.txt')
                ctx.exit(1)

            # Type assertion: stdin_content is guaranteed to be str here
            assert isinstance(stdin_content, str)

            # Format message with stdin content prepended
            msg = format_stdin_message(stdin_content, msg)
            logger.debug(f"Read {len(stdin_content)} bytes from stdin")

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            ctx.exit(1)

    # Process file attachments
    if files or globs:
        from consoul.cli.file_reader import (
            expand_glob_pattern,
            format_files_context,
        )

        try:
            # Collect all file paths
            all_files: list[Path] = []

            # Add explicitly specified files
            for file_path in files:
                all_files.append(Path(file_path).resolve())

            # Expand glob patterns
            for glob_pattern in globs:
                expanded = expand_glob_pattern(glob_pattern, max_files=50)
                all_files.extend(expanded)

            # Remove duplicates while preserving order
            seen = set()
            unique_files = []
            for f in all_files:
                if f not in seen:
                    seen.add(f)
                    unique_files.append(f)

            if not unique_files:
                console.print(
                    "[yellow]Warning: No files found matching patterns[/yellow]"
                )
            else:
                # Format file contents
                file_context = format_files_context(
                    unique_files, max_total_size=500_000
                )
                logger.info(f"Loaded {len(unique_files)} file(s)")

                # Prepend file context to message
                msg = f"{file_context}\n\n{msg}"

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            ctx.exit(1)
        except Exception as e:
            console.print(f"[red]Error reading files: {e}[/red]")
            ctx.exit(1)

    # Override model if specified
    if model:
        from consoul.ai.providers import get_provider_from_model

        config.current_model = model
        # Auto-detect provider from model name
        detected_provider = get_provider_from_model(model)
        if detected_provider:
            config.current_provider = detected_provider
            logger.info(
                f"Model override: {model} (provider: {detected_provider.value})"
            )
        else:
            logger.warning(
                f"Could not detect provider for model '{model}', using current provider: {config.current_provider.value}"
            )

    # Setup tools if requested
    tool_registry = None
    approval_provider = None

    tools_enabled = (
        tools
        if tools is not None
        else (config.tools.enabled if hasattr(config, "tools") else False)
    )

    if tools_enabled:
        try:
            from consoul.ai.tools import ToolRegistry
            from consoul.ai.tools.catalog import get_all_tool_names, get_tool_by_name

            # Create approval provider
            approval_provider = CliToolApprovalProvider(console=console)

            # Create registry with config settings
            tool_config = config.tools if hasattr(config, "tools") else None
            if tool_config:
                tool_registry = ToolRegistry(
                    config=tool_config,
                    approval_provider=approval_provider,
                )

                # Register available tools based on config filters
                allowed = tool_config.allowed_tools
                if allowed is not None:
                    tools_to_register: list[str] = list(allowed)
                else:
                    tools_to_register = get_all_tool_names()

                for tool_name in tools_to_register:
                    try:
                        result = get_tool_by_name(tool_name)
                        if result is None:
                            logger.warning(f"Tool {tool_name} not found in catalog")
                            continue

                        tool, risk_level, _ = result

                        # Apply risk filter if configured
                        if (
                            hasattr(tool_config, "risk_filter")
                            and tool_config.risk_filter
                        ):
                            from consoul.ai.tools import RiskLevel

                            # Map risk levels to numeric values for comparison
                            risk_order = {
                                RiskLevel.SAFE: 0,
                                RiskLevel.CAUTION: 1,
                                RiskLevel.DANGEROUS: 2,
                                RiskLevel.BLOCKED: 3,
                            }

                            max_risk = risk_order.get(tool_config.risk_filter, 0)
                            current_risk = risk_order.get(risk_level, 3)

                            if current_risk > max_risk:
                                logger.debug(
                                    f"Skipping {tool_name}: {risk_level.value} > {tool_config.risk_filter.value}"
                                )
                                continue

                        tool_registry.register(tool, risk_level=risk_level)
                    except Exception as e:
                        logger.warning(f"Could not register tool {tool_name}: {e}")

                logger.info(f"Registered {len(tool_registry)} tools")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not enable tools: {e}[/yellow]")
            tool_registry = None
            approval_provider = None

    # Handle attachments if provided
    if attach:
        # Check if model supports vision
        model_name = config.current_model.lower()
        vision_capable = any(
            vm in model_name
            for vm in ["claude-3", "gpt-4o", "gpt-4-vision", "gemini", "llava"]
        )

        if not vision_capable:
            console.print(
                f"[yellow]Warning: Model '{config.current_model}' may not support image analysis[/yellow]"
            )
            console.print(
                "[yellow]Consider using: claude-3-5-sonnet-20241022, gpt-4o, or gemini-2.0-flash[/yellow]\n"
            )

    # Get active profile and disable persistence for one-off query
    active_profile = config.get_active_profile()
    original_persist = None
    if hasattr(active_profile, "conversation"):
        original_persist = active_profile.conversation.persist
        active_profile.conversation.persist = False

    try:
        # Create chat session (no persistence for ask command)
        with console.status("[cyan]Initializing...[/cyan]", spinner="dots"):
            session = ChatSession(
                config=config,
                approval_provider=approval_provider,
                system_prompt_override=system_prompt,
            )

        # Handle attachments by appending to message
        if attach:
            # Add attachment references to message
            attachment_text = " ".join(str(Path(f).resolve()) for f in attach)
            msg = f"{msg} {attachment_text}"

        # Send message and get response
        response = session.send(
            msg,
            stream=stream,
            render_markdown=not no_markdown,
        )

        # Show token usage if requested
        if show_tokens or show_cost:
            console.print()
            stats = session.get_stats()

            if show_tokens:
                console.print(f"[dim]Tokens: {stats['token_count']:,}[/dim]")

            if show_cost:
                # Try to get cost info from last response
                try:
                    if (
                        hasattr(session.history, "messages")
                        and session.history.messages
                    ):
                        last_msg = session.history.messages[-1]
                        if (
                            hasattr(last_msg, "usage_metadata")
                            and last_msg.usage_metadata
                        ):
                            metadata = last_msg.usage_metadata
                            input_tokens = metadata.get("input_tokens", 0)
                            output_tokens = metadata.get("output_tokens", 0)

                            # Simple cost estimation (this is a rough estimate)
                            # Real implementation would use model-specific pricing
                            cost_per_m_input = 3.0  # $3 per million input tokens
                            cost_per_m_output = 15.0  # $15 per million output tokens

                            input_cost = (input_tokens / 1_000_000) * cost_per_m_input
                            output_cost = (
                                output_tokens / 1_000_000
                            ) * cost_per_m_output
                            total_cost = input_cost + output_cost

                            console.print(f"[dim]Cost: ${total_cost:.4f}[/dim]")
                except Exception as e:
                    logger.debug(f"Could not calculate cost: {e}")

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.write_text(response, encoding="utf-8")
            console.print(f"\n[dim]Response saved to: {output}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        ctx.exit(130)

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.error(f"Ask command error: {e}", exc_info=True)
        ctx.exit(1)

    finally:
        # Restore original persistence setting
        if original_persist is not None and hasattr(active_profile, "conversation"):
            active_profile.conversation.persist = original_persist


@cli.command()
@click.argument("config_path", type=click.Path(path_type=Path))
@click.pass_context
def init(ctx: click.Context, config_path: Path) -> None:
    """Initialize a new Consoul configuration file."""
    click.echo(f"Initializing config at: {config_path}")
    click.echo("Init functionality - Coming Soon!")


@cli.group()
@click.pass_context
def history(ctx: click.Context) -> None:
    """Manage conversation history."""
    pass


@history.command("list")
@click.option(
    "--limit",
    "-n",
    type=int,
    default=10,
    help="Number of conversations to show (default: 10)",
)
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def list_history(limit: int, db_path: Path | None) -> None:
    """List recent conversation sessions."""
    from consoul.ai.database import ConversationDatabase, DatabaseError

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        conversations = db.list_conversations(limit=limit)

        if not conversations:
            click.echo("No conversations found.")
            return

        click.echo(f"\nRecent conversations (showing {len(conversations)}):\n")
        for conv in conversations:
            session_id = conv["session_id"]
            model = conv["model"]
            created = conv["created_at"]
            updated = conv["updated_at"]
            msg_count = conv["message_count"]

            click.echo(f"Session ID: {session_id}")
            click.echo(f"  Model:    {model}")
            click.echo(f"  Messages: {msg_count}")
            click.echo(f"  Created:  {created}")
            click.echo(f"  Updated:  {updated}")
            click.echo()

    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("show")
@click.argument("session_id")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def show_history(session_id: str, db_path: Path | None) -> None:
    """Show conversation details for a specific session."""
    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")

        # Get metadata
        meta = db.get_conversation_metadata(session_id)

        click.echo(f"\nConversation: {session_id}\n")
        click.echo(f"Model:    {meta['model']}")
        click.echo(f"Messages: {meta['message_count']}")
        click.echo(f"Created:  {meta['created_at']}")
        click.echo(f"Updated:  {meta['updated_at']}")
        click.echo()

        # Get messages
        messages = db.load_conversation(session_id)

        if messages:
            click.echo("Messages:")
            click.echo("-" * 60)
            for i, msg in enumerate(messages, 1):
                role = msg["role"]
                content = msg["content"]
                tokens = msg.get("tokens", "?")

                # Truncate long messages
                if len(content) > 100:
                    content = content[:97] + "..."

                click.echo(f"{i}. {role.upper()} [{tokens} tokens]")
                click.echo(f"   {content}")
                click.echo()

    except ConversationNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("summary")
@click.argument("session_id")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def summary_history(session_id: str, db_path: Path | None) -> None:
    """Show conversation summary for a specific session."""
    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")

        # Get metadata
        meta = db.get_conversation_metadata(session_id)

        click.echo(f"\nConversation: {session_id}\n")
        click.echo(f"Model:    {meta['model']}")
        click.echo(f"Messages: {meta['message_count']}")
        click.echo(f"Created:  {meta['created_at']}")
        click.echo(f"Updated:  {meta['updated_at']}")
        click.echo()

        # Get summary
        summary = db.load_summary(session_id)

        if summary:
            click.echo("Summary:")
            click.echo("-" * 60)
            click.echo(summary)
            click.echo()
        else:
            click.echo("No summary available for this conversation.")
            click.echo(
                "Summaries are created automatically when using --summarize flag.\n"
            )

    except ConversationNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("search")
@click.argument("query")
@click.option(
    "--limit",
    "-n",
    type=int,
    default=20,
    help="Maximum number of results to return (default: 20)",
)
@click.option(
    "--model",
    help="Filter results by model name",
)
@click.option(
    "--after",
    help="Filter results after this date (ISO format: YYYY-MM-DD)",
)
@click.option(
    "--before",
    help="Filter results before this date (ISO format: YYYY-MM-DD)",
)
@click.option(
    "--context",
    "-c",
    type=int,
    default=2,
    help="Number of surrounding messages to show (default: 2)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format (default: text)",
)
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def search_history(
    query: str,
    limit: int,
    model: str | None,
    after: str | None,
    before: str | None,
    context: int,
    format: str,
    db_path: Path | None,
) -> None:
    """Search conversation history using full-text search.

    Query supports FTS5 syntax:
      - Basic: 'authentication bug'
      - Phrase: '"token limit exceeded"'
      - Prefix: 'auth*'
      - Boolean: 'bug AND NOT feature'

    Examples:
      consoul history search "authentication error"
      consoul history search '"token limit"' --model gpt-4o
      consoul history search "bug" --after 2025-01-01 --limit 10
    """
    import json

    from consoul.ai.database import ConversationDatabase, DatabaseError

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        results = db.search_messages(
            query=query,
            limit=limit,
            model_filter=model,
            after_date=after,
            before_date=before,
        )

        if not results:
            click.echo(f"No results found for: {query}")
            return

        if format == "json":
            # JSON output
            output = {
                "query": query,
                "total_results": len(results),
                "results": results,
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Text output
            click.echo(f"\nFound {len(results)} result(s) for: {query}\n")

            for i, result in enumerate(results, 1):
                click.echo("=" * 70)
                click.echo(
                    f"#{i} | Session: {result['session_id']} | Model: {result['model']}"
                )
                click.echo(f"    Timestamp: {result['timestamp']}")
                click.echo("-" * 70)

                # Show context if requested
                if context > 0:
                    try:
                        context_msgs = db.get_message_context(result["id"], context)
                        for msg in context_msgs:
                            role_label = msg["role"].upper()
                            is_match = msg["id"] == result["id"]
                            prefix = ">>> " if is_match else "    "
                            click.echo(f"{prefix}{role_label}:")

                            # Show snippet for matched message, full content for context
                            content = (
                                result["snippet"]
                                .replace("<mark>", "**")
                                .replace("</mark>", "**")
                                if is_match
                                else msg["content"][:200]
                            )
                            click.echo(f"{prefix}{content}")
                            click.echo()
                    except DatabaseError:
                        # Fallback to just showing the match
                        click.echo(f">>> {result['role'].upper()}:")
                        snippet = (
                            result["snippet"]
                            .replace("<mark>", "**")
                            .replace("</mark>", "**")
                        )
                        click.echo(f">>> {snippet}")
                        click.echo()
                else:
                    # Just show the snippet
                    click.echo(f">>> {result['role'].upper()}:")
                    snippet = (
                        result["snippet"]
                        .replace("<mark>", "**")
                        .replace("</mark>", "**")
                    )
                    click.echo(f">>> {snippet}")
                    click.echo()

                click.echo(
                    f"[View full conversation: consoul history show {result['session_id']}]"
                )
                click.echo()

    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("delete")
@click.argument("session_id")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
@click.confirmation_option(prompt="Are you sure you want to delete this conversation?")
def delete_history(session_id: str, db_path: Path | None) -> None:
    """Delete a conversation session."""
    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        db.delete_conversation(session_id)
        click.echo(f"Deleted conversation: {session_id}")

    except ConversationNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("clear")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
@click.confirmation_option(
    prompt="Are you sure you want to delete ALL conversations? This cannot be undone!"
)
def clear_history(db_path: Path | None) -> None:
    """Delete all conversation history."""
    from consoul.ai.database import ConversationDatabase, DatabaseError

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        count = db.clear_all_conversations()
        click.echo(f"Cleared {count} conversation(s)")

    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("stats")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def stats_history(db_path: Path | None) -> None:
    """Show conversation history statistics."""
    from consoul.ai.database import ConversationDatabase, DatabaseError

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        stats = db.get_stats()

        click.echo("\nConversation History Statistics\n")
        click.echo(f"Total conversations: {stats['total_conversations']}")
        click.echo(f"Total messages:      {stats['total_messages']}")
        click.echo(f"Database size:       {stats['db_size_bytes']:,} bytes")

        if stats["oldest_conversation"]:
            click.echo(f"Oldest conversation: {stats['oldest_conversation']}")
        if stats["newest_conversation"]:
            click.echo(f"Newest conversation: {stats['newest_conversation']}")

        click.echo()

    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("export")
@click.argument("session_id", required=False)
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "markdown", "html", "csv"], case_sensitive=False),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--all",
    is_flag=True,
    help="Export all conversations (JSON format only)",
)
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def export_history(
    session_id: str | None,
    output_file: Path,
    format: str,
    all: bool,
    db_path: Path | None,
) -> None:
    """Export conversation(s) to a file.

    Supported formats:
        - json: Structured JSON with full metadata (supports round-trip import)
        - markdown: Human-readable Markdown with formatting
        - html: Standalone HTML file with embedded styling
        - csv: CSV format for analytics (one row per message)

    Examples:
        consoul history export SESSION-ID output.json --format json
        consoul history export SESSION-ID output.md --format markdown
        consoul history export --all backup.json  # Export all conversations
    """
    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )
    from consoul.formatters import get_formatter
    from consoul.formatters.json_formatter import JSONFormatter

    try:
        # Validate arguments
        if all and session_id:
            click.echo("Error: Cannot specify both SESSION_ID and --all", err=True)
            sys.exit(1)

        if not all and not session_id:
            click.echo("Error: Must specify SESSION_ID or use --all", err=True)
            sys.exit(1)

        if all and format != "json":
            click.echo(
                "Error: --all flag only supports JSON format for consolidated backups",
                err=True,
            )
            sys.exit(1)

        db = ConversationDatabase(db_path or "~/.consoul/history.db")

        if all:
            # Export all conversations
            conversations = db.list_conversations(limit=10000)  # High limit for backup

            if not conversations:
                click.echo("No conversations found to export", err=True)
                sys.exit(1)

            # Fetch all conversation data
            conversations_data = []
            for conv in conversations:
                meta = db.get_conversation_metadata(conv["session_id"])
                messages = db.load_conversation(conv["session_id"])
                conversations_data.append((meta, messages))

            # Export using multi-conversation format
            json_output = JSONFormatter.export_multiple(conversations_data)
            output_file.write_text(json_output, encoding="utf-8")

            click.echo(f"Exported {len(conversations)} conversations to: {output_file}")

        else:
            # Export single conversation
            meta = db.get_conversation_metadata(session_id)  # type: ignore[arg-type]
            messages = db.load_conversation(session_id)  # type: ignore[arg-type]

            # Get formatter and export
            formatter = get_formatter(format)
            formatter.export_to_file(meta, messages, output_file)

            click.echo(f"Exported conversation to: {output_file}")

    except ConversationNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error exporting conversation: {e}", err=True)
        sys.exit(1)


@history.command("import")
@click.argument("import_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate import file without importing",
)
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def import_history(import_file: Path, dry_run: bool, db_path: Path | None) -> None:
    """Import conversations from Consoul JSON export.

    Supports both single conversation (v1.0) and multi-conversation (v1.0-multi) formats.
    This command restores conversations from backups created with the export command.

    Examples:
        consoul history import backup.json
        consoul history import backup.json --dry-run  # validate only
    """
    import json

    from consoul.ai.database import ConversationDatabase, DatabaseError
    from consoul.formatters.json_formatter import JSONFormatter

    try:
        # Read and parse import file
        try:
            data = json.loads(import_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            click.echo(f"Error: Invalid JSON file: {e}", err=True)
            sys.exit(1)

        # Validate structure
        try:
            JSONFormatter.validate_import_data(data)
        except ValueError as e:
            click.echo(f"Error: Invalid export format: {e}", err=True)
            sys.exit(1)

        version = data["version"]
        is_multi = version == JSONFormatter.VERSION_MULTI

        if dry_run:
            click.echo("✓ Validation successful")
            click.echo(f"  Version: {version}")
            click.echo(f"  Exported: {data['exported_at']}")

            if is_multi:
                click.echo(f"  Conversations: {data['conversation_count']}")
                for i, conv_data in enumerate(data["conversations"]):
                    conv = conv_data["conversation"]
                    click.echo(
                        f"    [{i + 1}] {conv['session_id']} - "
                        f"{conv['model']} - "
                        f"{len(conv_data['messages'])} messages"
                    )
            else:
                click.echo(f"  Session ID: {data['conversation']['session_id']}")
                click.echo(f"  Model: {data['conversation']['model']}")
                click.echo(f"  Messages: {len(data['messages'])}")
            return

        # Import conversation(s)
        db = ConversationDatabase(db_path or "~/.consoul/history.db")

        if is_multi:
            # Import multiple conversations
            imported_count = 0
            skipped_count = 0

            for conv_data in data["conversations"]:
                conv = conv_data["conversation"]
                session_id = conv["session_id"]

                # Check if conversation already exists
                try:
                    existing = db.get_conversation_metadata(session_id)
                    click.echo(
                        f"Warning: Conversation {session_id} already exists. Skipping."
                    )
                    skipped_count += 1
                    continue
                except Exception:
                    # Conversation doesn't exist, proceed with import
                    pass

                # Create conversation with original session_id
                db.create_conversation(model=conv["model"], session_id=session_id)

                # Import messages
                for msg in conv_data["messages"]:
                    db.save_message(
                        session_id=session_id,
                        role=msg["role"],
                        content=msg["content"],
                        tokens=msg.get("tokens"),
                        message_type=msg.get("message_type", msg["role"]),
                    )

                imported_count += 1

            click.echo("✓ Import complete")
            click.echo(f"  Imported: {imported_count} conversations")
            if skipped_count > 0:
                click.echo(f"  Skipped: {skipped_count} (already exist)")

        else:
            # Import single conversation
            conv = data["conversation"]
            session_id = conv["session_id"]

            # Check if conversation already exists
            try:
                existing = db.get_conversation_metadata(session_id)
                click.echo(
                    f"Warning: Conversation {session_id} already exists. Skipping import.",
                    err=True,
                )
                click.echo(
                    f"  Existing: created {existing['created_at']}, "
                    f"{existing['message_count']} messages"
                )
                sys.exit(1)
            except Exception:
                # Conversation doesn't exist, proceed with import
                pass

            # Create conversation with original session_id
            db.create_conversation(model=conv["model"], session_id=session_id)

            # Import messages
            for msg in data["messages"]:
                db.save_message(
                    session_id=session_id,
                    role=msg["role"],
                    content=msg["content"],
                    tokens=msg.get("tokens"),
                    message_type=msg.get("message_type", msg["role"]),
                )

            click.echo(f"✓ Imported conversation: {session_id}")
            click.echo(f"  Model: {conv['model']}")
            click.echo(f"  Messages: {len(data['messages'])}")

    except DatabaseError as e:
        click.echo(f"Error: Database error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error importing conversation: {e}", err=True)
        sys.exit(1)


@history.command("resume")
@click.argument("session_id")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
@click.option(
    "-m",
    "--model",
    help="Override model for resumed session",
)
@click.option(
    "--tools/--no-tools",
    default=None,
    help="Enable/disable tool execution",
)
@click.option(
    "--multiline",
    is_flag=True,
    help="Enable multi-line input mode (use Alt+Enter to submit)",
)
@click.option(
    "--no-stream",
    is_flag=True,
    help="Disable streaming responses",
)
@click.option(
    "--no-markdown",
    is_flag=True,
    help="Disable markdown rendering",
)
@click.pass_context
def resume_history(
    ctx: click.Context,
    session_id: str,
    db_path: Path | None,
    model: str | None,
    tools: bool | None,
    multiline: bool,
    no_stream: bool,
    no_markdown: bool,
) -> None:
    """Resume an existing conversation session.

    Load a previous conversation from the database and continue it in an interactive
    chat session. The session ID is preserved and new messages are appended to the
    existing conversation.

    Examples:
        # List conversations to find ID
        consoul history list

        # Resume a conversation
        consoul history resume abc123def456

        # Resume with model override
        consoul history resume abc123def456 --model gpt-4o

        # Resume with tools enabled
        consoul history resume abc123def456 --tools
    """
    import logging

    from rich.console import Console
    from rich.panel import Panel

    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )
    from consoul.cli import ChatSession, CliToolApprovalProvider, get_user_input

    logger = logging.getLogger(__name__)
    console = Console()
    config = ctx.obj["config"]

    # Verify session exists and get metadata
    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        meta = db.get_conversation_metadata(session_id)
        messages = db.load_conversation(session_id)
    except ConversationNotFoundError:
        console.print(f"[red]Error: Session '{session_id}' not found[/red]")
        console.print(
            "\n[dim]Use 'consoul history list' to see available sessions[/dim]"
        )
        ctx.exit(1)
    except DatabaseError as e:
        console.print(f"[red]Database error: {e}[/red]")
        ctx.exit(1)

    # Show what we're resuming
    console.print()
    resume_info = (
        f"[bold]Session ID:[/bold] {session_id}\n"
        f"[bold]Original Model:[/bold] {meta['model']}\n"
        f"[bold]Messages:[/bold] {meta['message_count']}\n"
        f"[bold]Last Updated:[/bold] {meta['updated_at']}"
    )

    # Override model if specified
    if model:
        from consoul.ai.providers import get_provider_from_model

        config.current_model = model
        # Auto-detect provider from model name
        detected_provider = get_provider_from_model(model)
        if detected_provider:
            config.current_provider = detected_provider
            logger.info(
                f"Model override: {model} (provider: {detected_provider.value})"
            )
            resume_info += f"\n[bold]Override Model:[/bold] {model}"
        else:
            logger.warning(
                f"Could not detect provider for model '{model}', using current provider: {config.current_provider.value}"
            )

    console.print(
        Panel(
            resume_info,
            title="[bold cyan]Resuming Conversation[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    # Show last few messages for context
    if messages:
        console.print("[dim]Last 3 messages for context:[/dim]")
        console.print("[dim]" + "─" * 60 + "[/dim]")
        for msg in messages[-3:]:
            role = msg["role"]
            content = msg["content"]
            # Truncate long messages
            if len(content) > 100:
                content = content[:97] + "..."
            console.print(f"[dim]{role.upper()}: {content}[/dim]")
        console.print("[dim]" + "─" * 60 + "[/dim]")
        console.print()

    # Setup tool registry if tools enabled
    tool_registry = None
    approval_provider = None
    tools_enabled = (
        tools
        if tools is not None
        else (config.tools.enabled if hasattr(config, "tools") else False)
    )

    if tools_enabled:
        try:
            from consoul.ai.tools import ToolRegistry
            from consoul.ai.tools.catalog import get_all_tool_names, get_tool_by_name

            # Create approval provider first
            approval_provider = CliToolApprovalProvider(console=console)

            # Create registry with config settings
            tool_config = config.tools if hasattr(config, "tools") else None
            if tool_config:
                tool_registry = ToolRegistry(
                    config=tool_config,
                    approval_provider=approval_provider,
                )

                # Register available tools based on config filters
                allowed = tool_config.allowed_tools
                if allowed is not None:
                    # Explicit whitelist (may be empty list = no tools)
                    tools_to_register: list[str] = list(allowed)
                else:
                    # No whitelist - use all tools subject to risk filter
                    tools_to_register = get_all_tool_names()

                for tool_name in tools_to_register:
                    try:
                        result = get_tool_by_name(tool_name)
                        if result is None:
                            logger.warning(f"Tool {tool_name} not found in catalog")
                            continue

                        tool, risk_level, _ = result

                        # Apply risk filter if configured
                        if (
                            hasattr(tool_config, "risk_filter")
                            and tool_config.risk_filter
                        ):
                            from consoul.ai.tools import RiskLevel

                            # Map risk levels to numeric values for comparison
                            risk_order = {
                                RiskLevel.SAFE: 0,
                                RiskLevel.CAUTION: 1,
                                RiskLevel.DANGEROUS: 2,
                                RiskLevel.BLOCKED: 3,
                            }

                            max_risk = risk_order.get(tool_config.risk_filter, 0)
                            current_risk = risk_order.get(risk_level, 3)

                            if current_risk > max_risk:
                                logger.debug(
                                    f"Skipping {tool_name}: {risk_level.value} > {tool_config.risk_filter.value}"
                                )
                                continue

                        tool_registry.register(tool, risk_level=risk_level)
                    except Exception as e:
                        logger.warning(f"Could not register tool {tool_name}: {e}")

                logger.info(f"Registered {len(tool_registry)} tools")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not enable tools: {e}[/yellow]")
            tool_registry = None
            approval_provider = None

    # Create chat session with resume_session_id
    try:
        with console.status("[cyan]Initializing chat model...[/cyan]", spinner="dots"):
            session = ChatSession(
                config=config,
                approval_provider=approval_provider,
                resume_session_id=session_id,
            )
    except Exception as e:
        console.print(f"[red]Error initializing chat session: {e}[/red]")
        logger.error(f"Failed to initialize ChatSession: {e}", exc_info=True)
        ctx.exit(1)

    # Main chat loop (same as chat command)
    with session:
        while True:
            try:
                # Get user input
                user_input = get_user_input(
                    prompt_text="You: ",
                    multiline=multiline,
                )

                # Handle exit (Ctrl+D or 'exit' command)
                if user_input is None:
                    break

                # Skip empty input (re-prompt)
                if not user_input:
                    continue

                # Check for slash commands
                if session.process_command(user_input):
                    # Command was handled, check if exit was requested
                    if session.should_exit:
                        break
                    # Otherwise continue to next prompt
                    continue

                # Send message and get response
                response = session.send(
                    user_input,
                    stream=not no_stream,
                    render_markdown=not no_markdown,
                )

                logger.debug(f"Response received: {response[:100]}...")

            except KeyboardInterrupt:
                # Ctrl+C - exit gracefully
                console.print("\n[yellow]Cancelled[/yellow]")
                break

            except Exception as e:
                # API errors, rate limits, network issues
                console.print(f"\n[red]Error: {e}[/red]\n")
                logger.error(f"Chat error: {e}", exc_info=True)
                # Continue loop, don't exit on errors
                continue

        # Display session stats on exit
        console.print()
        stats = session.get_stats()

        stats_text = (
            f"[bold]Messages:[/bold] {stats['message_count']}\n"
            f"[bold]Tokens:[/bold] {stats['token_count']:,}"
        )

        # Session is always persisted when resuming
        stats_text += f"\n\n[dim]Session saved (ID: {session_id})[/dim]"

        console.print(
            Panel(
                stats_text,
                title="[bold cyan]Session Summary[/bold cyan]",
                border_style="cyan",
            )
        )

        console.print("\n[dim]Goodbye![/dim]\n")


@cli.group()
@click.pass_context
def preset(ctx: click.Context) -> None:
    """Manage tool presets."""
    pass


def _create_describe_command() -> click.Command:
    """Factory function to create the describe command with proper CLI access."""

    @click.command(name="describe")
    @click.argument("command_path", nargs=-1)
    @click.option(
        "--format",
        "-f",
        type=click.Choice(["json", "markdown"], case_sensitive=False),
        default="json",
        help="Output format (default: json)",
    )
    @click.option(
        "--output",
        "-o",
        type=click.Path(path_type=Path),
        help="Write output to file instead of stdout",
    )
    @click.option(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation spaces (default: 2)",
    )
    @click.option(
        "--compact",
        is_flag=True,
        help="Compact JSON output (no indentation)",
    )
    @click.pass_context
    def describe_cmd(
        ctx: click.Context,
        command_path: tuple[str, ...],
        format: str,
        output: Path | None,
        indent: int,
        compact: bool,
    ) -> None:
        """Describe Consoul CLI commands and their schemas.

        By default, outputs CLI structure as JSON for compatibility with
        documentation generators and AI agents.

        Examples:

            \b
            # Show all commands structure
            consoul describe

            \b
            # Describe specific command
            consoul describe tui

            \b
            # Output to file
            consoul describe --output cli-schema.json

            \b
            # Markdown format
            consoul describe --format markdown
        """
        from consoul.commands.describe import get_app_schema, get_command_info

        # Walk up the context chain to find the root CLI group
        root_ctx = ctx
        while root_ctx.parent is not None:
            root_ctx = root_ctx.parent

        cli_app = root_ctx.command
        if not isinstance(cli_app, click.Group):
            click.echo("Error: Could not access CLI application", err=True)
            sys.exit(1)

        # Get schema for specific command or entire app
        if command_path:
            # Navigate to specific command
            current = cli_app
            full_path = "consoul"

            for cmd_name in command_path:
                if not isinstance(current, click.Group):
                    click.echo(f"Error: '{full_path}' is not a group command", err=True)
                    sys.exit(1)

                cmd = current.get_command(click.Context(current), cmd_name)
                if not cmd:
                    click.echo(
                        f"Error: Command '{cmd_name}' not found in '{full_path}'",
                        err=True,
                    )
                    sys.exit(1)

                current = cmd
                full_path = f"{full_path} {cmd_name}"

            schema = get_command_info(
                current,
                " ".join(["consoul", *command_path[:-1]])
                if len(command_path) > 1
                else "",
            )
        else:
            schema = get_app_schema(cli_app)

        # Format output
        import json

        if format.lower() == "json":
            if compact:
                json_str = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
            else:
                json_str = json.dumps(schema, indent=indent, ensure_ascii=False)

            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json_str, encoding="utf-8")
                click.echo(f"Schema written to: {output}")
            else:
                click.echo(json_str)

        elif format.lower() == "markdown":
            # Basic markdown output (will be enhanced with templates later)
            click.echo("Markdown format coming soon - use JSON for now")
            click.echo(
                "Run: consoul describe --format json | python scripts/generate_docs.py"
            )

    return describe_cmd


# Add the describe command to CLI
cli.add_command(_create_describe_command())


@preset.command("list")
@click.pass_context
def list_presets(ctx: click.Context) -> None:
    """List all available tool presets (built-in + custom).

    Shows preset name, description, and tools included.

    Examples:
        consoul preset list
    """
    from consoul.ai.tools.presets import list_available_presets
    from consoul.config import load_config

    # Load config to get custom presets
    config = load_config()

    # Get all presets (built-in + custom)
    all_presets = list_available_presets(config.tool_presets)

    click.echo("\nAvailable Tool Presets:\n")

    # Built-in presets
    builtin_names = {"readonly", "development", "safe-research", "power-user"}
    builtin_presets = {k: v for k, v in all_presets.items() if k in builtin_names}
    custom_presets = {k: v for k, v in all_presets.items() if k not in builtin_names}

    if builtin_presets:
        click.echo("Built-in Presets:")
        for name in sorted(builtin_presets.keys()):
            preset_obj = builtin_presets[name]
            tools_count = len(preset_obj.tools)
            tools_display = ", ".join(preset_obj.tools[:5])
            if tools_count > 5:
                tools_display += f", ... ({tools_count - 5} more)"

            click.echo(f"  {name}")
            click.echo(f"    Description: {preset_obj.description}")
            click.echo(f"    Tools: {tools_display}")
            click.echo()

    if custom_presets:
        click.echo("Custom Presets:")
        for name in sorted(custom_presets.keys()):
            preset_obj = custom_presets[name]
            tools_count = len(preset_obj.tools)
            tools_display = ", ".join(preset_obj.tools[:5])
            if tools_count > 5:
                tools_display += f", ... ({tools_count - 5} more)"

            click.echo(f"  {name}")
            click.echo(f"    Description: {preset_obj.description}")
            click.echo(f"    Tools: {tools_display}")
            click.echo()

    click.echo(f"Total: {len(all_presets)} presets available")
    click.echo("\nUse with: consoul tui --preset <preset-name>")


def main() -> None:
    """Main entry point for Consoul CLI."""
    # Register TUI command if Textual is available
    try:
        from consoul.tui.cli import tui

        cli.add_command(tui)
    except ImportError:
        # TUI dependencies not installed, CLI will work without TUI subcommand
        pass

    # Register release command
    try:
        from consoul.commands.release import release

        cli.add_command(release)
    except ImportError:
        # Release dependencies may not be available
        pass

    cli(obj={})


if __name__ == "__main__":
    main()
