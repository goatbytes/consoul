"""CLI entry point for Consoul TUI.

This module provides the command-line interface for launching the Consoul
Terminal User Interface.
"""

from __future__ import annotations

import click

from consoul.tui.app import ConsoulApp
from consoul.tui.config import TuiConfig

__all__ = ["tui"]


@click.command()
@click.option("--theme", help="Color theme (monokai, dracula, nord, gruvbox)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--log-file", type=click.Path(), help="Debug log file path")
@click.option(
    "--tools",
    type=str,
    help="Tool specification: 'all', 'none', 'safe', 'caution', 'dangerous', "
    "category names (search/file-edit/web/execute), "
    "or comma-separated tool names (bash,grep,code_search)",
)
@click.option("--test-mode", is_flag=True, hidden=True, help="Test mode (auto-exit)")
@click.pass_context
def tui(
    ctx: click.Context,
    theme: str | None,
    debug: bool,
    log_file: str | None,
    tools: str | None,
    test_mode: bool,
) -> None:
    """Launch Consoul TUI.

    Interactive terminal user interface for AI conversations with streaming
    responses, conversation history, and keyboard-driven navigation.

    Examples:
        $ consoul tui
        $ consoul tui --theme dracula
        $ consoul --model gpt-4o tui
        $ consoul tui --tools safe
        $ consoul tui --tools bash,grep,code_search
        $ consoul tui --tools search,web
        $ consoul tui --tools none
    """
    # Apply macOS PyTorch fixes BEFORE any imports that might trigger torch/transformers
    # This must happen at the very start to prevent segfaults
    import platform

    if platform.system() == "Darwin":
        from consoul.ai.macos_fixes import apply_macos_pytorch_fixes

        apply_macos_pytorch_fixes()

    from consoul.config import load_config

    # Load Consoul config first to get TUI settings
    consoul_config = None

    # Get CLI context from parent command
    parent_ctx = ctx.parent
    if parent_ctx and parent_ctx.params:
        # Check if we have a model override
        model_override = parent_ctx.params.get("model")

        if model_override:
            # Load full config first to preserve TUI and other settings
            consoul_config = load_config()

            # Determine provider and create provider config
            from consoul.config.models import Provider, ProviderConfig

            provider: Provider
            if "gpt" in model_override.lower() or "o1" in model_override.lower():
                provider = Provider.OPENAI
            elif "claude" in model_override.lower():
                provider = Provider.ANTHROPIC
            elif "gemini" in model_override.lower():
                provider = Provider.GOOGLE
            else:
                provider = Provider.OLLAMA

            # Build provider config with CLI overrides
            temp = parent_ctx.params.get("temperature")
            max_tok = parent_ctx.params.get("max_tokens")

            # Update provider config with CLI overrides
            if provider not in consoul_config.provider_configs:
                consoul_config.provider_configs[provider] = ProviderConfig()

            if temp is not None:
                consoul_config.provider_configs[provider].default_temperature = temp
            if max_tok is not None:
                consoul_config.provider_configs[provider].default_max_tokens = max_tok

            # Override model and provider
            consoul_config.current_provider = provider
            consoul_config.current_model = model_override
        else:
            # Load default config
            consoul_config = load_config()
    else:
        consoul_config = load_config()

    # Handle --tools CLI override
    if tools is not None:
        from consoul.ai.tools.catalog import parse_and_resolve_tools

        try:
            # Parse and resolve tools specification
            tools_to_register = parse_and_resolve_tools(tools)

            # Normalize to actual tool.name values for execution whitelist
            # This ensures friendly names like "bash" work with ToolRegistry.is_allowed()
            # which checks against tool.name like "bash_execute"
            normalized_tool_names = [
                tool.name for tool, _risk, _cats in tools_to_register
            ]

            # Override config with CLI tools specification
            consoul_config.tools.allowed_tools = normalized_tool_names

        except ValueError as e:
            # Show error and exit
            import sys

            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    # Get TUI config from loaded config, then apply CLI overrides
    if consoul_config:
        # consoul_config.tui should be a TuiConfig object
        # If it's a dict (shouldn't happen but defensive check), convert it
        if isinstance(consoul_config.tui, dict):
            tui_config = TuiConfig(**consoul_config.tui)
        else:
            tui_config = consoul_config.tui
    else:
        tui_config = TuiConfig()

    # Apply CLI overrides
    if theme:
        tui_config.theme = theme
    if debug:
        tui_config.debug = True
    if log_file:
        tui_config.log_file = log_file

    # Set up logging if debug mode enabled
    if tui_config.debug:
        import logging

        log_path = tui_config.log_file or "textual.log"

        # Configure root logger to WARNING to suppress third-party debug spam
        # (urllib3, httpcore, httpx, markdown_it, asyncio all log at DEBUG)
        # Only log to file, not to console (StreamHandler would overlap TUI)
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_path, mode="w")],
        )

        # Enable debug logging ONLY for our packages
        logging.getLogger("textual").setLevel(logging.DEBUG)
        logging.getLogger("consoul").setLevel(logging.DEBUG)

        # Explicitly silence noisy third-party loggers
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("markdown_it").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

        # Create a logger to confirm setup
        logger = logging.getLogger(__name__)
        logger.info(f"Debug logging enabled, writing to: {log_path}")

    import contextlib

    app = ConsoulApp(
        config=tui_config, consoul_config=consoul_config, test_mode=test_mode
    )

    # Handle Ctrl+C gracefully - exit without error
    with contextlib.suppress(KeyboardInterrupt):
        app.run()


if __name__ == "__main__":
    tui()
