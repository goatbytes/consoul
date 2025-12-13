"""Modal helper utilities for TUI.

Provides reusable helper functions for displaying common modal patterns
including text modals, markdown modals, and library browser modals.
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from textual.app import App, ComposeResult
    from textual.screen import Screen

logger = logging.getLogger(__name__)

__all__ = [
    "create_screensaver_screen",
    "show_ollama_library_modal",
    "show_system_prompt_modal",
]


async def show_system_prompt_modal(
    app: App[Any],
    system_prompt: str,
    profile_name: str | None = None,
    tool_count: int | None = None,
    stored_at: str | None = None,
) -> None:
    """Show system prompt in a modal dialog.

    Args:
        app: Textual app instance
        system_prompt: System prompt text to display
        profile_name: Optional profile name
        tool_count: Optional tool count
        stored_at: Optional timestamp when prompt was stored
    """
    from consoul.tui.widgets.system_prompt_modal import SystemPromptModal

    logger.info("[MODAL] Showing system prompt modal")

    await app.push_screen(
        SystemPromptModal(
            system_prompt=system_prompt,
            profile_name=profile_name,
            tool_count=tool_count,
            stored_at=stored_at,
        )
    )


async def show_ollama_library_modal(app: App[Any]) -> None:
    """Show Ollama Library browser modal.

    Args:
        app: Textual app instance

    Raises:
        ImportError: If beautifulsoup4 is not installed
    """
    from consoul.tui.widgets.ollama_library_modal import OllamaLibraryModal

    logger.info("[MODAL] Showing Ollama library modal")

    await app.push_screen(OllamaLibraryModal())


def create_screensaver_screen(theme_name: str | None = None) -> Screen[None]:
    """Create a screensaver screen with random animation.

    Args:
        theme_name: Optional theme name for color scheme

    Returns:
        ScreensaverScreen instance ready to be pushed to screen stack
    """
    from textual.screen import Screen

    from consoul.tui.animations import AnimationStyle
    from consoul.tui.loading import LoadingScreen

    # Select random animation style
    animation_styles = [
        AnimationStyle.SOUND_WAVE,
        AnimationStyle.MATRIX_RAIN,
        AnimationStyle.BINARY_WAVE,
        AnimationStyle.CODE_STREAM,
        AnimationStyle.PULSE,
    ]
    style = random.choice(animation_styles)

    # Determine color scheme from theme
    color_scheme = (
        theme_name
        if theme_name
        in [
            "consoul-dark",
            "consoul-light",
            "consoul-oled",
            "consoul-midnight",
            "consoul-matrix",
            "consoul-sunset",
            "consoul-ocean",
            "consoul-volcano",
            "consoul-neon",
            "consoul-forest",
        ]
        else "consoul-dark"
    )

    class ScreensaverScreen(Screen[None]):
        """Screensaver screen that covers entire terminal."""

        DEFAULT_CSS = """
        ScreensaverScreen {
            layout: vertical;
            height: 100vh;
            padding: 0;
            margin: 0;
        }

        ScreensaverScreen > LoadingScreen {
            width: 100%;
            height: 100%;
            padding: 0;
            margin: 0;
        }

        ScreensaverScreen > LoadingScreen > Center {
            display: none;
        }
        """

        def __init__(self, animation_style: AnimationStyle, color_scheme: str) -> None:
            super().__init__()
            self.animation_style = animation_style
            self.color_scheme = color_scheme

        def on_mount(self) -> None:
            """Hide docked widgets when screen mounts."""
            # Hide docked widgets (Footer, ContextualTopBar) to ensure screensaver covers everything
            for widget in self.app.query("Footer, ContextualTopBar"):
                widget.display = False

        def compose(self) -> ComposeResult:
            yield LoadingScreen(
                message="",
                style=self.animation_style,
                color_scheme=self.color_scheme,  # type: ignore
                show_progress=False,
            )

        def on_key(self, event: Any) -> None:
            """Dismiss on any key press and restore docked widgets."""
            # Restore docked widgets visibility
            for widget in self.app.query("Footer, ContextualTopBar"):
                widget.display = True
            self.app.pop_screen()

    logger.info(f"[SCREENSAVER] Created screensaver with {style} animation")
    return ScreensaverScreen(style, color_scheme)
