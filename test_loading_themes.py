#!/usr/bin/env python3
"""Test script to preview different Consoul themes and Pygments syntax styles.

This script allows you to interactively test different combinations of:
- Consoul themes (for background colors and UI)
- Pygments syntax highlighting styles (for code colors)

Usage:
    python test_loading_themes.py
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Select, Static

from consoul.tui.animations import AnimationStyle
from consoul.tui.loading import LoadingScreen


class ThemeTesterApp(App[None]):
    """App to test different theme and syntax highlighting combinations."""

    CSS = """
    Screen {
        align: center middle;
    }

    #controls {
        width: 80;
        height: auto;
        background: $panel;
        padding: 1 2;
        margin: 1;
    }

    #preview-container {
        width: 100%;
        height: 30;
        border: solid $primary;
        margin: 1;
    }

    .control-row {
        height: 3;
        margin: 1 0;
        align: left middle;
    }

    .label {
        width: 20;
        height: 3;
        content-align: right middle;
        padding-right: 1;
    }

    Select {
        width: 50;
    }

    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
        ("r", "refresh_preview", "Refresh"),
    ]

    # Available Consoul themes
    CONSOUL_THEMES: ClassVar[list[str]] = [
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

    # Available Pygments styles (all 49)
    PYGMENTS_STYLES: ClassVar[list[str]] = [
        "abap",
        "algol",
        "algol_nu",
        "arduino",
        "autumn",
        "borland",
        "bw",
        "coffee",
        "colorful",
        "default",
        "dracula",
        "emacs",
        "friendly",
        "friendly_grayscale",
        "fruity",
        "github-dark",
        "gruvbox-dark",
        "gruvbox-light",
        "igor",
        "inkpot",
        "lightbulb",
        "lilypond",
        "lovelace",
        "manni",
        "material",
        "monokai",
        "murphy",
        "native",
        "nord",
        "nord-darker",
        "one-dark",
        "paraiso-dark",
        "paraiso-light",
        "pastie",
        "perldoc",
        "rainbow_dash",
        "rrt",
        "sas",
        "solarized-dark",
        "solarized-light",
        "staroffice",
        "stata-dark",
        "stata-light",
        "tango",
        "trac",
        "vim",
        "vs",
        "xcode",
        "zenburn",
    ]

    def __init__(self):
        super().__init__()
        self.current_consoul_theme = "consoul-dark"
        self.current_pygments_style = "monokai"
        self.preview_widget: LoadingScreen | None = None

    def compose(self) -> ComposeResult:
        """Compose the test app layout."""
        yield Header()

        with Vertical(id="controls"):
            yield Static("[b]Theme Tester[/b]", classes="title")
            yield Static("")

            with Horizontal(classes="control-row"):
                yield Static("Consoul Theme:", classes="label")
                yield Select(
                    [(theme, theme) for theme in self.CONSOUL_THEMES],
                    value=self.current_consoul_theme,
                    id="consoul-theme-select",
                    allow_blank=False,
                )

            with Horizontal(classes="control-row"):
                yield Static("Syntax Style:", classes="label")
                yield Select(
                    [(style, style) for style in self.PYGMENTS_STYLES],
                    value=self.current_pygments_style,
                    id="pygments-style-select",
                    allow_blank=False,
                )

            yield Button("Apply & Preview", id="apply-button", variant="primary")
            yield Static("", id="info")

        with Container(id="preview-container"):
            self.preview_widget = LoadingScreen(
                message="",
                style=AnimationStyle.CODE_STREAM,
                color_scheme=self.current_consoul_theme,  # type: ignore
                show_progress=False,
            )
            yield self.preview_widget

        yield Footer()

    def on_mount(self) -> None:
        """Update info on mount."""
        self._update_info()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select dropdown changes."""
        if event.select.id == "consoul-theme-select":
            self.current_consoul_theme = str(event.value)
        elif event.select.id == "pygments-style-select":
            self.current_pygments_style = str(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle apply button press."""
        if event.button.id == "apply-button":
            self.action_refresh_preview()

    def action_refresh_preview(self) -> None:
        """Refresh the preview with current settings."""
        # Remove old preview
        if self.preview_widget:
            self.preview_widget.remove()

        # Create new preview with updated settings
        container = self.query_one("#preview-container")
        self.preview_widget = LoadingScreen(
            message="",
            style=AnimationStyle.CODE_STREAM,
            color_scheme=self.current_consoul_theme,  # type: ignore
            show_progress=False,
        )
        container.mount(self.preview_widget)

        # Update the animator's Pygments style directly
        if self.preview_widget:
            try:
                canvas = self.preview_widget.query_one("BinaryCanvas")
                if hasattr(canvas, "animator") and canvas.animator:
                    # Import here to update the theme
                    from consoul.tui.animations import BinaryAnimator

                    size = canvas.size
                    # Create new animator with custom Pygments style
                    canvas.animator = BinaryAnimator(
                        size.width,
                        size.height,
                        AnimationStyle.CODE_STREAM,
                        theme=self.current_pygments_style,  # Use Pygments style directly
                    )
            except Exception as e:
                self.notify(f"Error updating animator: {e}", severity="error")

        self._update_info()
        # self.notify(
        #     f"Preview updated: {self.current_consoul_theme} + {self.current_pygments_style}",
        #     title="Applied"
        # )

    def _update_info(self) -> None:
        """Update the info display."""
        info = self.query_one("#info", Static)
        info.update(
            f"[b]Current:[/b]\n"
            f"Theme: [cyan]{self.current_consoul_theme}[/cyan]\n"
            f"Syntax: [cyan]{self.current_pygments_style}[/cyan]"
        )


if __name__ == "__main__":
    app = ThemeTesterApp()
    app.run()
