"""Loading screen widget with animations for Consoul.

This module provides a branded loading screen with binary/waveform animations
that displays during Consoul TUI initialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from rich.console import RenderableType
    from textual.app import ComposeResult

from rich.style import Style
from rich.text import Text
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Label, Static

from consoul.tui.animations import AnimationStyle, BinaryAnimator

__all__ = ["BinaryCanvas", "ConsoulLoadingScreen", "LoadingScreen"]


class BinaryCanvas(Static):
    """A canvas widget that renders binary animations."""

    DEFAULT_CSS = """
    BinaryCanvas {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(
        self,
        style: AnimationStyle = AnimationStyle.SOUND_WAVE,
        color_scheme: Literal["green", "blue", "cyan", "magenta", "rainbow"] = "blue",
    ) -> None:
        """Initialize the binary canvas.

        Args:
            style: Animation style to use
            color_scheme: Color scheme for the animation
        """
        super().__init__()
        self.animation_style = style
        self.color_scheme = color_scheme
        self.animator: BinaryAnimator | None = None

        # Color maps for animations
        self._color_map = {
            "green": ["#002200", "#004400", "#006600", "#00aa00", "#00ff00"],
            "blue": ["#001a33", "#003366", "#0055aa", "#0077cc", "#0085CC"],
            "cyan": ["#001a1a", "#003333", "#005555", "#007777", "#009999"],
            "magenta": ["#220022", "#440044", "#660066", "#aa00aa", "#ff00ff"],
            "rainbow": ["#ff0000", "#ff7700", "#ffff00", "#00ff00", "#0000ff"],
        }

    def on_mount(self) -> None:
        """Initialize the animator when mounted."""
        size = self.size
        self.animator = BinaryAnimator(size.width, size.height, self.animation_style)
        self.set_interval(1 / 30, self._update_animation)

    def _update_animation(self) -> None:
        """Update the animation frame."""
        if self.animator:
            self.animator.advance()
            self.refresh()

    def _get_color_for_intensity(self, intensity: int) -> str:
        """Get color based on intensity (0-100)."""
        colors = self._color_map[self.color_scheme]
        idx = min(int(intensity / 100 * len(colors)), len(colors) - 1)
        return colors[idx]

    def render(self) -> RenderableType:
        """Render the binary animation."""
        if not self.animator:
            return Text()

        size = self.size
        if size.width != self.animator.width or size.height != self.animator.height:
            self.animator = BinaryAnimator(
                size.width, size.height, self.animation_style
            )

        # Create a grid for the characters
        grid: dict[tuple[int, int], tuple[str, int, str | None]] = {}
        frame = self.animator.get_frame()

        for x, y, char, intensity, syntax_color in frame:
            if 0 <= x < size.width and 0 <= y < size.height:
                grid[(x, y)] = (char, intensity, syntax_color)

        # Build the rendered text
        text = Text()
        for y in range(size.height):
            for x in range(size.width):
                if (x, y) in grid:
                    char, intensity, syntax_color = grid[(x, y)]
                    # Use syntax color if provided, otherwise use intensity-based color
                    color = syntax_color or self._get_color_for_intensity(intensity)
                    text.append(char, style=Style(color=color))
                else:
                    text.append(" ")
            if y < size.height - 1:
                text.append("\n")

        return text


class LoadingScreen(Widget):
    """A loading screen with binary animations.

    This widget displays an animated binary pattern with an optional
    loading message and progress indicator.
    """

    DEFAULT_CSS = """
    LoadingScreen {
        width: 100%;
        height: 100%;
        background: $surface;
        layers: bg overlay;
    }

    LoadingScreen > BinaryCanvas {
        layer: bg;
        width: 100%;
        height: 100%;
    }

    LoadingScreen > Center {
        layer: overlay;
    }

    LoadingScreen > Center > Middle {
        width: auto;
        height: auto;
    }

    LoadingScreen .message {
        text-align: center;
        color: $primary;
        text-style: bold;
    }

    LoadingScreen > .progress-bar {
        layer: overlay;
        dock: bottom;
        width: 100%;
        height: 1;
    }
    """

    def __init__(
        self,
        message: str = "Loading Consoul...",
        style: AnimationStyle = AnimationStyle.SOUND_WAVE,
        color_scheme: Literal["green", "blue", "cyan", "magenta", "rainbow"] = "blue",
        show_progress: bool = False,
    ) -> None:
        """Initialize the loading screen.

        Args:
            message: Loading message to display
            style: Animation style to use
            color_scheme: Color scheme for the animation
            show_progress: Whether to show a progress indicator
        """
        super().__init__()
        self.message = message
        self.animation_style = style
        self.color_scheme = color_scheme
        self.show_progress = show_progress
        self._progress = 0

    def compose(self) -> ComposeResult:
        """Compose the loading screen layout."""
        yield BinaryCanvas(
            style=self.animation_style,
            color_scheme=self.color_scheme,
        )

        with Center(), Middle():
            yield Label(self.message, classes="message")

        if self.show_progress:
            yield Static("", classes="progress-bar", id="progress-bar")

    def update_message(self, message: str) -> None:
        """Update the loading message.

        Args:
            message: New message to display
        """
        self.message = message
        try:
            label = self.query_one(".message", Label)
            label.update(message)
        except Exception:
            pass  # Widget not mounted yet

    def update_progress(self, progress: int) -> None:
        """Update the progress indicator.

        Args:
            progress: Progress percentage (0-100)
        """
        if not self.show_progress:
            return

        self._progress = max(0, min(100, progress))
        try:
            progress_bar = self.query_one("#progress-bar", Static)
            bar_width = progress_bar.size.width
            if bar_width > 0:
                filled = int(bar_width * self._progress / 100)
                bar_text = "▬" * filled + "─" * (bar_width - filled)

                # Add percentage text in the center
                percent_text = f" {self._progress}% "
                center_pos = (bar_width - len(percent_text)) // 2
                if center_pos >= 0 and center_pos + len(percent_text) <= bar_width:
                    bar_text = (
                        bar_text[:center_pos]
                        + percent_text
                        + bar_text[center_pos + len(percent_text) :]
                    )

                text = Text()
                for i, char in enumerate(bar_text):
                    if i < filled:
                        text.append(char, style=Style(color="#0085CC", dim=False))
                    else:
                        text.append(char, style=Style(color="#44385E", dim=True))

                progress_bar.update(text)
        except Exception:
            pass  # Progress bar not mounted yet


class ConsoulLoadingScreen(Screen[None]):
    """Loading screen for Consoul TUI application.

    This screen displays during app initialization and provides visual
    feedback to the user.
    """

    CSS = """
    ConsoulLoadingScreen {
        align: center middle;
    }
    """

    def __init__(
        self,
        animation_style: AnimationStyle = AnimationStyle.SOUND_WAVE,
        show_progress: bool = True,
    ) -> None:
        """Initialize the Consoul loading screen.

        Args:
            animation_style: Animation style to display
            show_progress: Whether to show progress bar
        """
        super().__init__()
        self.animation_style = animation_style
        self.show_progress = show_progress
        self.loading_widget: LoadingScreen | None = None

    def compose(self) -> ComposeResult:
        """Compose the loading screen."""
        self.loading_widget = LoadingScreen(
            message="Initializing Consoul...",
            style=self.animation_style,
            color_scheme="blue",
            show_progress=self.show_progress,
        )
        yield self.loading_widget

    def update_progress(self, message: str, progress: int) -> None:
        """Update loading progress.

        Args:
            message: Loading status message
            progress: Progress percentage (0-100)
        """
        if self.loading_widget:
            self.loading_widget.update_message(message)
            self.loading_widget.update_progress(progress)

    async def fade_out(self, duration: float = 1.0) -> None:
        """Fade out the loading screen.

        Args:
            duration: Fade duration in seconds
        """
        if self.loading_widget:
            self.loading_widget.styles.animate("opacity", value=0.0, duration=duration)
            import asyncio

            await asyncio.sleep(duration)
