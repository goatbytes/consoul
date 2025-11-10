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
@click.option("--test-mode", is_flag=True, hidden=True, help="Test mode (auto-exit)")
def tui(theme: str | None, test_mode: bool) -> None:
    """Launch Consoul TUI.

    Interactive terminal user interface for AI conversations with streaming
    responses, conversation history, and keyboard-driven navigation.

    Examples:
        $ consoul tui
        $ consoul tui --theme dracula
    """
    config = TuiConfig()
    if theme:
        config.theme = theme

    app = ConsoulApp(config=config, test_mode=test_mode)
    app.run()


if __name__ == "__main__":
    tui()
