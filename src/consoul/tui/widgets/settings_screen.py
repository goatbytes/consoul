"""SettingsScreen - Modal dialog for application settings."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.config import ConsoulConfig
    from consoul.tui.config import TuiConfig

__all__ = ["SettingsScreen"]


class SettingsScreen(ModalScreen[bool]):
    """Modal dialog for editing application settings.

    Allows user to:
    - Edit TUI configuration settings
    - Organize settings by category (Appearance, Performance, Behavior, Advanced)
    - Preview theme and sidebar changes live
    - Save to global or project config file
    - Validate settings before applying
    """

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }

    SettingsScreen > Vertical {
        width: 90;
        height: auto;
        max-height: 90%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    SettingsScreen .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
    }

    SettingsScreen TabbedContent {
        width: 100%;
        height: auto;
        max-height: 35;
        background: transparent;
        border: none;
        margin: 0 0 1 0;
    }

    SettingsScreen TabPane {
        padding: 1;
    }

    SettingsScreen .setting-row {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin: 0 0 1 0;
    }

    SettingsScreen .setting-label {
        width: 40%;
        content-align: left middle;
        color: $text;
    }

    SettingsScreen .setting-control {
        width: 60%;
        height: auto;
    }

    SettingsScreen Input {
        width: 100%;
    }

    SettingsScreen Select {
        width: 100%;
    }

    SettingsScreen Switch {
        width: auto;
    }

    SettingsScreen RadioSet {
        width: 100%;
        height: auto;
        background: transparent;
        border: none;
        padding: 0;
    }

    SettingsScreen RadioButton {
        width: 100%;
        background: transparent;
        margin: 0;
        padding: 0 1;
    }

    SettingsScreen .validation-error {
        width: 100%;
        color: $error;
        text-align: center;
        margin: 0 0 1 0;
        min-height: 1;
    }

    SettingsScreen .save-location {
        width: 100%;
        color: $accent;
        text-align: center;
        margin: 0 0 1 0;
    }

    SettingsScreen .button-container {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin: 1 0 0 0;
    }

    SettingsScreen Button {
        min-width: 16;
        margin: 0 1;
    }

    SettingsScreen .apply-button {
        background: $accent;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(
        self,
        config: TuiConfig,
        consoul_config: ConsoulConfig,
        **kwargs: Any,
    ) -> None:
        """Initialize settings screen.

        Args:
            config: Current TUI configuration
            consoul_config: Full Consoul configuration
            **kwargs: Additional arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.config = config
        self.consoul_config = consoul_config
        self._original_config = config.model_copy(deep=True)
        self._applying = False
        self._mounted = False
        self._theme_preview_timer: asyncio.Task[None] | None = None

    def compose(self) -> ComposeResult:
        """Compose the settings screen layout."""
        with Vertical():
            yield Label("Settings", classes="modal-title")

            with TabbedContent():
                with TabPane("Appearance"):
                    yield from self._compose_appearance_tab()

                with TabPane("Performance"):
                    yield from self._compose_performance_tab()

                with TabPane("Behavior"):
                    yield from self._compose_behavior_tab()

                with TabPane("Advanced"):
                    yield from self._compose_advanced_tab()

            # Validation error display
            yield Static(
                "", id="validation-error", classes="validation-error", markup=False
            )

            # Save location info
            yield Static("", id="save-location", classes="save-location")

            # Buttons
            with Horizontal(classes="button-container"):
                yield Button("Apply", variant="primary", id="apply-button")
                yield Button("Reset", variant="default", id="reset-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def _compose_appearance_tab(self) -> ComposeResult:
        """Compose the Appearance tab contents."""
        # Theme selection
        with Horizontal(classes="setting-row"):
            yield Label("Theme:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Select(
                    options=[
                        ("Monokai", "monokai"),
                        ("Dracula", "dracula"),
                        ("Nord", "nord"),
                        ("Gruvbox", "gruvbox"),
                        ("Tokyo Night", "tokyo-night"),
                        ("Catppuccin Mocha", "catppuccin-mocha"),
                        ("Catppuccin Latte", "catppuccin-latte"),
                        ("Solarized Light", "solarized-light"),
                        ("Flexoki", "flexoki"),
                        ("Textual Dark", "textual-dark"),
                        ("Textual Light", "textual-light"),
                        ("Textual ANSI", "textual-ansi"),
                    ],
                    value=self.config.theme,
                    id="setting-theme",
                )

        # Show sidebar
        with Horizontal(classes="setting-row"):
            yield Label("Show Sidebar:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(value=self.config.show_sidebar, id="setting-show_sidebar")

        # Show timestamps
        with Horizontal(classes="setting-row"):
            yield Label("Show Timestamps:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(
                    value=self.config.show_timestamps, id="setting-show_timestamps"
                )

        # Show token count
        with Horizontal(classes="setting-row"):
            yield Label("Show Token Count:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(
                    value=self.config.show_token_count, id="setting-show_token_count"
                )

        # Input syntax highlighting
        with Horizontal(classes="setting-row"):
            yield Label("Input Syntax Highlighting:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(
                    value=self.config.input_syntax_highlighting,
                    id="setting-input_syntax_highlighting",
                )

    def _compose_performance_tab(self) -> ComposeResult:
        """Compose the Performance tab contents."""
        # GC mode
        with Horizontal(classes="setting-row"):
            yield Label("Garbage Collection Mode:", classes="setting-label")
            with Vertical(classes="setting-control"), RadioSet(id="setting-gc_mode"):
                yield RadioButton("Auto", id="gc_mode-auto")
                yield RadioButton("Manual", id="gc_mode-manual")
                yield RadioButton("Streaming-Aware", id="gc_mode-streaming-aware")

        # GC generation
        with Horizontal(classes="setting-row"):
            yield Label("GC Generation:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Input(
                    value=str(self.config.gc_generation),
                    placeholder="0 (default)",
                    id="setting-gc_generation",
                )

        # GC interval
        with Horizontal(classes="setting-row"):
            yield Label("GC Interval (seconds):", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Input(
                    value=str(self.config.gc_interval_seconds),
                    placeholder="30.0 (default)",
                    id="setting-gc_interval_seconds",
                )

        # Stream buffer size
        with Horizontal(classes="setting-row"):
            yield Label("Stream Buffer Size:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Input(
                    value=str(self.config.stream_buffer_size),
                    placeholder="200 (default)",
                    id="setting-stream_buffer_size",
                )

        # Stream debounce ms
        with Horizontal(classes="setting-row"):
            yield Label("Stream Debounce (ms):", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Input(
                    value=str(self.config.stream_debounce_ms),
                    placeholder="150 (default)",
                    id="setting-stream_debounce_ms",
                )

        # Enable virtualization
        with Horizontal(classes="setting-row"):
            yield Label("Enable Virtualization:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(
                    value=self.config.enable_virtualization,
                    id="setting-enable_virtualization",
                )

        # Initial conversation load
        with Horizontal(classes="setting-row"):
            yield Label("Initial Conversation Load:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Input(
                    value=str(self.config.initial_conversation_load),
                    placeholder="50 (default)",
                    id="setting-initial_conversation_load",
                )

    def _compose_behavior_tab(self) -> ComposeResult:
        """Compose the Behavior tab contents."""
        # Stream renderer
        with Horizontal(classes="setting-row"):
            yield Label("Stream Renderer:", classes="setting-label")
            with (
                Vertical(classes="setting-control"),
                RadioSet(id="setting-stream_renderer"),
            ):
                yield RadioButton("Markdown", id="stream_renderer-markdown")
                yield RadioButton("Rich Log", id="stream_renderer-richlog")
                yield RadioButton("Hybrid", id="stream_renderer-hybrid")

        # Auto-generate titles
        with Horizontal(classes="setting-row"):
            yield Label("Auto-Generate Titles:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(
                    value=self.config.auto_generate_titles,
                    id="setting-auto_generate_titles",
                )

        # Auto-title max tokens
        with Horizontal(classes="setting-row"):
            yield Label("Auto-Title Max Tokens:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Input(
                    value=str(self.config.auto_title_max_tokens),
                    placeholder="20 (default)",
                    id="setting-auto_title_max_tokens",
                )

        # Auto-title temperature
        with Horizontal(classes="setting-row"):
            yield Label("Auto-Title Temperature:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Input(
                    value=str(self.config.auto_title_temperature),
                    placeholder="0.7 (default)",
                    id="setting-auto_title_temperature",
                )

        # Enable multiline input
        with Horizontal(classes="setting-row"):
            yield Label("Multiline Input:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(
                    value=self.config.enable_multiline_input,
                    id="setting-enable_multiline_input",
                )

    def _compose_advanced_tab(self) -> ComposeResult:
        """Compose the Advanced tab contents."""
        # Debug mode
        with Horizontal(classes="setting-row"):
            yield Label("Debug Mode:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(value=self.config.debug, id="setting-debug")

        # Enable mouse
        with Horizontal(classes="setting-row"):
            yield Label("Enable Mouse:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(value=self.config.enable_mouse, id="setting-enable_mouse")

        # Vim mode
        with Horizontal(classes="setting-row"):
            yield Label("Vim Mode:", classes="setting-label")
            with Vertical(classes="setting-control"):
                yield Switch(value=self.config.vim_mode, id="setting-vim_mode")

    def on_mount(self) -> None:
        """Initialize settings screen after mounting."""
        # Mark as mounted FIRST to prevent any change events from being processed
        # while we're still initializing values
        self._mounted = False  # Keep disabled during initialization

        self._update_save_location()

        # Verify theme select has correct value
        try:
            theme_select = self.query_one("#setting-theme", Select)
            # If value doesn't match config, force it
            if str(theme_select.value) != self.config.theme:
                theme_select.value = self.config.theme
        except Exception:
            pass

        # Set initial radio button selections
        # GC mode
        try:
            gc_mode_map = {
                "auto": "gc_mode-auto",
                "manual": "gc_mode-manual",
                "streaming-aware": "gc_mode-streaming-aware",
            }
            button_id = gc_mode_map.get(self.config.gc_mode)
            if button_id:
                button = self.query_one(f"#{button_id}", RadioButton)
                button.value = True
        except Exception:
            pass

        # Stream renderer
        try:
            renderer_map = {
                "markdown": "stream_renderer-markdown",
                "richlog": "stream_renderer-richlog",
                "hybrid": "stream_renderer-hybrid",
            }
            button_id = renderer_map.get(self.config.stream_renderer)
            if button_id:
                button = self.query_one(f"#{button_id}", RadioButton)
                button.value = True
        except Exception:
            pass

        # NOW enable preview handlers - all initialization is complete
        self._mounted = True

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes."""
        # Only apply preview if fully mounted (ignore programmatic changes during init)
        if not self._mounted:
            return

        if event.select.id == "setting-theme":
            # Debounce theme preview to avoid flickering during arrow key navigation
            # Cancel any pending preview
            if self._theme_preview_timer is not None:
                self._theme_preview_timer.cancel()

            # Schedule preview after 300ms delay
            async def delayed_preview() -> None:
                await asyncio.sleep(0.3)
                await self._apply_theme_preview(str(event.value))

            self._theme_preview_timer = asyncio.create_task(delayed_preview())

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch widget changes."""
        # Only apply preview if fully mounted (ignore programmatic changes during init)
        if not self._mounted:
            return

        if event.switch.id == "setting-show_sidebar":
            # Live preview sidebar toggle
            await self._apply_sidebar_preview(event.value)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-button":
            await self._revert_preview()
            self.dismiss(False)
        elif event.button.id == "reset-button":
            await self._reset_to_original()
        elif event.button.id == "apply-button" and not self._applying:
            await self._apply_settings()

    def action_cancel(self) -> None:
        """Cancel the modal."""
        if not self._applying:
            self.app.call_later(self._revert_and_dismiss)

    async def _revert_and_dismiss(self) -> None:
        """Revert preview changes and dismiss."""
        await self._revert_preview()
        self.dismiss(False)

    async def _apply_theme_preview(self, theme: str) -> None:
        """Apply theme change as live preview.

        Args:
            theme: Theme name to preview
        """
        with suppress(Exception):
            # Set app theme (Textual built-in themes)
            self.app.theme = theme

    async def _apply_sidebar_preview(self, show: bool) -> None:
        """Apply sidebar visibility change as live preview.

        Args:
            show: Whether to show sidebar
        """
        try:
            # Post message to toggle sidebar (temporary preview)
            from consoul.tui.widgets.conversation_list import ConversationList

            sidebar = self.app.query_one(ConversationList)
            if show and not sidebar.display:
                sidebar.display = True
            elif not show and sidebar.display:
                sidebar.display = False
        except Exception:
            pass  # Silently ignore if sidebar not found

    async def _revert_preview(self) -> None:
        """Revert any live preview changes."""
        try:
            # Revert theme
            self.app.theme = self._original_config.theme

            # Revert sidebar
            from consoul.tui.widgets.conversation_list import ConversationList

            sidebar = self.app.query_one(ConversationList)
            if self._original_config.show_sidebar and not sidebar.display:
                sidebar.display = True
            elif not self._original_config.show_sidebar and sidebar.display:
                sidebar.display = False
        except Exception:
            pass

    async def _reset_to_original(self) -> None:
        """Reset all settings to original values."""
        # Reset switches
        for switch_id in [
            "show_sidebar",
            "show_timestamps",
            "show_token_count",
            "input_syntax_highlighting",
            "enable_virtualization",
            "auto_generate_titles",
            "enable_multiline_input",
            "debug",
            "enable_mouse",
            "vim_mode",
        ]:
            try:
                switch = self.query_one(f"#setting-{switch_id}", Switch)
                switch.value = getattr(self._original_config, switch_id)
            except Exception:
                pass

        # Reset inputs
        for input_id in [
            "gc_generation",
            "gc_interval_seconds",
            "stream_buffer_size",
            "stream_debounce_ms",
            "initial_conversation_load",
            "auto_title_max_tokens",
            "auto_title_temperature",
        ]:
            try:
                input_widget = self.query_one(f"#setting-{input_id}", Input)
                input_widget.value = str(getattr(self._original_config, input_id))
            except Exception:
                pass

        # Reset selects
        try:
            theme_select = self.query_one("#setting-theme", Select)
            theme_select.value = self._original_config.theme
        except Exception:
            pass

        # Reset radio sets
        try:
            gc_mode_set = self.query_one("#setting-gc_mode", RadioSet)
            for button in gc_mode_set.query(RadioButton):
                button_id = str(button.id)
                if button_id.endswith(self._original_config.gc_mode):
                    button.value = (
                        True  # Press the button instead of setting pressed_button
                    )
                    break
        except Exception:
            pass

        try:
            renderer_set = self.query_one("#setting-stream_renderer", RadioSet)
            for button in renderer_set.query(RadioButton):
                button_id = str(button.id)
                if button_id.endswith(self._original_config.stream_renderer):
                    button.value = (
                        True  # Press the button instead of setting pressed_button
                    )
                    break
        except Exception:
            pass

        # Revert preview
        await self._revert_preview()

        # Clear validation error
        try:
            error_label = self.query_one("#validation-error", Static)
            error_label.update("")
        except Exception:
            pass

    async def _apply_settings(self) -> None:
        """Collect settings from widgets, validate, and save."""
        self._applying = True

        try:
            # Disable buttons during apply
            apply_btn = self.query_one("#apply-button", Button)
            reset_btn = self.query_one("#reset-button", Button)
            cancel_btn = self.query_one("#cancel-button", Button)
            apply_btn.disabled = True
            reset_btn.disabled = True
            cancel_btn.disabled = True

            error_label = self.query_one("#validation-error", Static)
            error_label.update("")

            # Collect values from widgets
            settings: dict[str, Any] = {}

            # Switches
            for switch_id in [
                "show_sidebar",
                "show_timestamps",
                "show_token_count",
                "input_syntax_highlighting",
                "enable_virtualization",
                "auto_generate_titles",
                "enable_multiline_input",
                "debug",
                "enable_mouse",
                "vim_mode",
            ]:
                try:
                    switch = self.query_one(f"#setting-{switch_id}", Switch)
                    settings[switch_id] = switch.value
                except Exception:
                    pass

            # Inputs (integers and floats)
            int_inputs = [
                "gc_generation",
                "stream_buffer_size",
                "stream_debounce_ms",
                "initial_conversation_load",
                "auto_title_max_tokens",
            ]
            float_inputs = ["gc_interval_seconds", "auto_title_temperature"]

            for input_id in int_inputs:
                try:
                    input_widget = self.query_one(f"#setting-{input_id}", Input)
                    settings[input_id] = int(input_widget.value)
                except ValueError:
                    error_label.update(
                        f"✗ Invalid number for {input_id.replace('_', ' ')}"
                    )
                    apply_btn.disabled = False
                    reset_btn.disabled = False
                    cancel_btn.disabled = False
                    self._applying = False
                    return
                except Exception:
                    pass

            for input_id in float_inputs:
                try:
                    input_widget = self.query_one(f"#setting-{input_id}", Input)
                    settings[input_id] = float(input_widget.value)
                except ValueError:
                    error_label.update(
                        f"✗ Invalid number for {input_id.replace('_', ' ')}"
                    )
                    apply_btn.disabled = False
                    reset_btn.disabled = False
                    cancel_btn.disabled = False
                    self._applying = False
                    return
                except Exception:
                    pass

            # Selects
            try:
                theme_select = self.query_one("#setting-theme", Select)
                settings["theme"] = str(theme_select.value)
            except Exception:
                pass

            # Radio sets
            try:
                gc_mode_set = self.query_one("#setting-gc_mode", RadioSet)
                if gc_mode_set.pressed_button:
                    button_id = str(gc_mode_set.pressed_button.id)
                    # Split on first hyphen only: "gc_mode-streaming-aware" -> "streaming-aware"
                    settings["gc_mode"] = button_id.split("-", 1)[1]
            except Exception:
                pass

            try:
                renderer_set = self.query_one("#setting-stream_renderer", RadioSet)
                if renderer_set.pressed_button:
                    button_id = str(renderer_set.pressed_button.id)
                    # Split on first hyphen only: "stream_renderer-richlog" -> "richlog"
                    settings["stream_renderer"] = button_id.split("-", 1)[1]
            except Exception:
                pass

            # Validate settings using Pydantic
            try:
                # Create new config with updated values
                from consoul.tui.config import TuiConfig

                new_config = TuiConfig(**{**self.config.model_dump(), **settings})
            except Exception as e:
                error_label.update(f"✗ Validation error: {e}")
                apply_btn.disabled = False
                reset_btn.disabled = False
                cancel_btn.disabled = False
                self._applying = False
                return

            # Save configuration
            await asyncio.sleep(0)  # Allow UI update
            error_label.update("Saving settings...")

            try:
                from consoul.config.loader import find_config_files, save_config

                # Determine save location
                global_path, project_path = find_config_files()

                # Use project config if it exists, otherwise global
                save_path = (
                    project_path
                    if project_path and project_path.exists()
                    else global_path
                )

                if not save_path:
                    # Default to global config
                    save_path = Path.home() / ".consoul" / "config.yaml"
                    save_path.parent.mkdir(parents=True, exist_ok=True)

                # Update consoul_config with new TUI config
                self.consoul_config.tui = new_config

                # Save to file
                save_config(self.consoul_config, save_path, include_api_keys=False)

                # Update current config reference
                self.config.__dict__.update(new_config.__dict__)
                self._original_config = new_config.model_copy(deep=True)

                error_label.update(f"✓ Settings saved to {save_path.name}")
                await asyncio.sleep(1)

                # Dismiss with success
                self.dismiss(True)

            except Exception as e:
                error_label.update(f"✗ Failed to save: {e}")
                apply_btn.disabled = False
                reset_btn.disabled = False
                cancel_btn.disabled = False
                self._applying = False

        except Exception as e:
            # Show error
            error_label = self.query_one("#validation-error", Static)
            error_label.update(f"✗ Error: {e}")

            # Re-enable buttons
            apply_btn = self.query_one("#apply-button", Button)
            reset_btn = self.query_one("#reset-button", Button)
            cancel_btn = self.query_one("#cancel-button", Button)
            apply_btn.disabled = False
            reset_btn.disabled = False
            cancel_btn.disabled = False

            self._applying = False

    def _update_save_location(self) -> None:
        """Update the save location info label."""
        try:
            from consoul.config.loader import find_config_files

            global_path, project_path = find_config_files()
            save_path = (
                project_path if project_path and project_path.exists() else global_path
            )

            if save_path:
                location_type = "project" if save_path == project_path else "global"
                location_label = self.query_one("#save-location", Static)
                location_label.update(
                    f"Saving to {location_type} config: {save_path.name}"
                )
            else:
                location_label = self.query_one("#save-location", Static)
                location_label.update("Saving to global config: config.yaml")
        except Exception:
            pass
