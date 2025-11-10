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
@click.option("--test-mode", is_flag=True, hidden=True, help="Test mode (auto-exit)")
@click.pass_context
def tui(
    ctx: click.Context,
    theme: str | None,
    debug: bool,
    log_file: str | None,
    test_mode: bool,
) -> None:
    """Launch Consoul TUI.

    Interactive terminal user interface for AI conversations with streaming
    responses, conversation history, and keyboard-driven navigation.

    Examples:
        $ consoul tui
        $ consoul tui --theme dracula
        $ consoul --model gpt-4o tui
    """
    from consoul.config import load_config

    tui_config = TuiConfig()
    if theme:
        tui_config.theme = theme
    if debug:
        tui_config.debug = True
    if log_file:
        tui_config.log_file = log_file

    # Load Consoul config and apply CLI overrides
    consoul_config = None

    # Get CLI context from parent command
    parent_ctx = ctx.parent
    if parent_ctx and parent_ctx.params:
        # Check if we have a model override
        model_override = parent_ctx.params.get("model")

        if model_override:
            # Create a minimal config with the overridden model
            # Determine provider and create provider config
            from consoul.config.models import (
                ConsoulConfig,
                ProfileConfig,
                Provider,
                ProviderConfig,
            )

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

            provider_config = ProviderConfig(
                default_temperature=temp if temp is not None else 1.0,
                default_max_tokens=max_tok if max_tok is not None else 4096,
            )

            # Create simple profile (no model, just settings)
            profile = ProfileConfig(
                name="cli-override",
                description=f"CLI override with {model_override}",
                system_prompt="You are a helpful AI assistant.",
            )

            # Create config with provider/model at root level
            consoul_config = ConsoulConfig(
                profiles={"cli-override": profile},
                active_profile="cli-override",
                current_provider=provider,
                current_model=model_override,
                provider_configs={provider: provider_config},
            )
        else:
            # Load default config
            consoul_config = load_config()
    else:
        consoul_config = load_config()

    # Set up logging if debug mode enabled
    if tui_config.debug:
        import logging

        log_path = tui_config.log_file or "textual.log"

        # Configure root logger
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_path, mode="w"), logging.StreamHandler()],
        )

        # Enable debug logging for our widgets
        logging.getLogger("textual").setLevel(logging.DEBUG)
        logging.getLogger("consoul").setLevel(logging.DEBUG)

        # Create a logger to confirm setup
        logger = logging.getLogger(__name__)
        logger.info(f"Debug logging enabled, writing to: {log_path}")

    app = ConsoulApp(
        config=tui_config, consoul_config=consoul_config, test_mode=test_mode
    )
    app.run()


if __name__ == "__main__":
    tui()
