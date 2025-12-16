#!/usr/bin/env python3
"""Standalone test of the Consoul loading screen.

This demo shows the loading screen without requiring full consoul installation.
Run with: python examples/test_loading_standalone.py
"""

import asyncio
import sys
from pathlib import Path
from typing import ClassVar

# Direct imports without going through consoul package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import only the TUI modules we need
from consoul.tui import animations, loading

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, Label


class AnimationSelector(App):
    """Simple app to test loading screen animations."""

    CSS = """
    Screen {
        align: center middle;
    }

    Vertical {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    Label {
        text-align: center;
        width: 100%;
    }

    .title {
        text-style: bold;
        background: $primary;
        color: $text;
        margin-bottom: 1;
    }

    Button {
        width: 100%;
        margin: 0 0 1 0;
    }
    """

    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the selector UI."""
        yield Header()
        yield Vertical(
            Label("Consoul Loading Screen Test", classes="title"),
            Label("Select an animation style to preview:"),
            Button("Sound Wave (Logo Style)", id="sound-wave", variant="primary"),
            Button("Matrix Rain", id="matrix-rain"),
            Button("Binary Wave", id="binary-wave"),
            Button("Code Stream", id="code-stream"),
            Button("Pulse", id="pulse"),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        animation_map = {
            "sound-wave": animations.AnimationStyle.SOUND_WAVE,
            "matrix-rain": animations.AnimationStyle.MATRIX_RAIN,
            "binary-wave": animations.AnimationStyle.BINARY_WAVE,
            "code-stream": animations.AnimationStyle.CODE_STREAM,
            "pulse": animations.AnimationStyle.PULSE,
        }

        if event.button.id in animation_map:
            self.show_loading(animation_map[event.button.id])

    def show_loading(self, animation_style: animations.AnimationStyle) -> None:
        """Show the loading screen with selected animation."""
        loading_screen = loading.ConsoulLoadingScreen(
            animation_style=animation_style, show_progress=True
        )
        self.push_screen(loading_screen)
        self.simulate_loading(loading_screen)

    @work
    async def simulate_loading(self, loading_screen: loading.ConsoulLoadingScreen) -> None:
        """Simulate loading with progress updates."""
        loading_steps = [
            ("Initializing Consoul...", 20),
            ("Loading AI models...", 40),
            ("Connecting to providers...", 60),
            ("Loading conversation history...", 80),
            ("Finalizing...", 100),
        ]

        for message, progress in loading_steps:
            loading_screen.update_progress(message, progress)
            await asyncio.sleep(1.0)

        # Show completion message
        loading_screen.update_progress("Ready!", 100)
        await asyncio.sleep(0.5)

        # Fade out and return to selector
        await loading_screen.fade_out(duration=1.0)
        self.pop_screen()


def main() -> None:
    """Run the test app."""
    app = AnimationSelector()
    app.run()


if __name__ == "__main__":
    main()
