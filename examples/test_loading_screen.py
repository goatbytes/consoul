#!/usr/bin/env python3
"""Test the Consoul loading screen.

This demo shows the loading screen with different animation styles.
"""

import asyncio
import sys
from pathlib import Path
from typing import ClassVar

# Add src to path for development testing
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, Label

from consoul.tui.animations import AnimationStyle
from consoul.tui.loading import ConsoulLoadingScreen


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
            "sound-wave": AnimationStyle.SOUND_WAVE,
            "matrix-rain": AnimationStyle.MATRIX_RAIN,
            "binary-wave": AnimationStyle.BINARY_WAVE,
            "code-stream": AnimationStyle.CODE_STREAM,
            "pulse": AnimationStyle.PULSE,
        }

        if event.button.id in animation_map:
            self.show_loading(animation_map[event.button.id])

    def show_loading(self, animation_style: AnimationStyle) -> None:
        """Show the loading screen with selected animation."""
        loading_screen = ConsoulLoadingScreen(
            animation_style=animation_style, show_progress=True
        )
        self.push_screen(loading_screen)
        self.simulate_loading(loading_screen)

    @work
    async def simulate_loading(self, loading_screen: ConsoulLoadingScreen) -> None:
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
