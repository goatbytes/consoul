"""MLX Model Conversion Modal for converting HuggingFace models to MLX format.

This module provides a UI for converting local PyTorch HuggingFace models to
Apple's MLX format with quantization options and progress tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ProgressBar, RadioButton, RadioSet

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["MLXConversionModal"]


class MLXConversionModal(ModalScreen[dict[str, str | int | bool] | None]):
    """Modal for converting HuggingFace models to MLX format.

    Allows users to:
    - Select quantization level (4-bit, 8-bit, or none)
    - See estimated output size
    - Track conversion progress
    - Cancel conversion mid-process

    Returns dict with conversion parameters on start, None on cancel.
    """

    DEFAULT_CSS = """
    MLXConversionModal {
        align: center middle;
    }

    MLXConversionModal > Container {
        width: 70;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    MLXConversionModal .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }

    MLXConversionModal .model-info {
        width: 100%;
        padding: 1 0;
        color: $text-muted;
    }

    MLXConversionModal RadioSet {
        width: 100%;
        padding: 1 0;
    }

    MLXConversionModal RadioButton {
        width: 100%;
    }

    MLXConversionModal .size-estimate {
        width: 100%;
        padding: 1 0;
        color: $success;
        text-style: italic;
    }

    MLXConversionModal .warning {
        width: 100%;
        padding: 1 0;
        color: $warning;
        text-style: italic;
    }

    MLXConversionModal ProgressBar {
        width: 100%;
        margin: 1 0;
    }

    MLXConversionModal .progress-label {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        padding: 0 0 1 0;
    }

    MLXConversionModal .modal-actions {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
        padding: 1 0 0 0;
    }

    MLXConversionModal Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        model_name: str,
        model_size_gb: float,
        **kwargs: Any,
    ) -> None:
        """Initialize conversion modal.

        Args:
            model_name: HuggingFace model identifier (e.g., "Qwen/Qwen3-8B")
            model_size_gb: Size of original model in GB
            **kwargs: Additional arguments passed to ModalScreen
        """
        super().__init__(**kwargs)
        self.model_name = model_name
        self.model_size_gb = model_size_gb
        self.converting = False
        self.selected_quantization = "4bit"  # Default to 4-bit

    def compose(self) -> ComposeResult:
        """Compose the modal widgets."""
        with Container():
            yield Label("Convert Model to MLX", classes="modal-title")

            yield Label(
                f"Model: {self.model_name}\nOriginal size: {self.model_size_gb:.1f}GB",
                classes="model-info",
            )

            yield Label("Quantization Level:", classes="modal-title")

            with RadioSet(id="quantization-options"):
                yield RadioButton(
                    "4-bit (Recommended - ~4x smaller, good quality)",
                    value=True,
                    id="quant-4bit",
                )
                yield RadioButton(
                    "8-bit (Better quality, ~2x smaller)",
                    id="quant-8bit",
                )
                yield RadioButton(
                    "None (Full precision, same size)",
                    id="quant-none",
                )

            self.size_label = Label(
                self._get_size_estimate("4bit"),
                classes="size-estimate",
                id="size-estimate",
            )
            yield self.size_label

            yield Label(
                "⚠️  Conversion may take 5-30 minutes depending on model size",
                classes="warning",
            )

            # Progress section (hidden initially)
            with Vertical(id="progress-section"):
                self.progress_label = Label(
                    "Starting conversion...",
                    classes="progress-label",
                    id="progress-label",
                )
                yield self.progress_label

                self.progress_bar = ProgressBar(
                    total=100,
                    show_eta=False,
                    id="conversion-progress",
                )
                self.progress_bar.display = False  # Hidden until conversion starts
                yield self.progress_bar

            with Horizontal(classes="modal-actions"):
                yield Button("Start Conversion", variant="primary", id="start-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def _get_size_estimate(self, quantization: str) -> str:
        """Get estimated size after conversion.

        Args:
            quantization: One of "4bit", "8bit", or "none"

        Returns:
            Human-readable size estimate string
        """
        if quantization == "4bit":
            estimated_gb = self.model_size_gb / 4
            return f"Estimated size after conversion: ~{estimated_gb:.1f}GB"
        elif quantization == "8bit":
            estimated_gb = self.model_size_gb / 2
            return f"Estimated size after conversion: ~{estimated_gb:.1f}GB"
        else:
            return f"Estimated size after conversion: ~{self.model_size_gb:.1f}GB"

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle quantization option changes.

        Args:
            event: RadioSet changed event
        """
        if event.radio_set.id != "quantization-options":
            return

        # Update selected quantization
        pressed_id = event.pressed.id if event.pressed else None
        if pressed_id == "quant-4bit":
            self.selected_quantization = "4bit"
        elif pressed_id == "quant-8bit":
            self.selected_quantization = "8bit"
        elif pressed_id == "quant-none":
            self.selected_quantization = "none"

        # Update size estimate
        self.size_label.update(self._get_size_estimate(self.selected_quantization))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button pressed event
        """
        if event.button.id == "start-button":
            if not self.converting:
                # Return conversion parameters
                quantize = self.selected_quantization != "none"
                q_bits = (
                    4
                    if self.selected_quantization == "4bit"
                    else 8
                    if quantize
                    else 4  # Default for safety
                )

                result: dict[str, str | int | bool] = {
                    "model_name": self.model_name,
                    "quantize": quantize,
                    "q_bits": q_bits,
                }
                self.dismiss(result)

        elif event.button.id == "cancel-button":
            self.dismiss(None)

    def update_progress(self, progress: float, message: str = "") -> None:
        """Update conversion progress.

        Args:
            progress: Progress percentage (0-100)
            message: Progress message to display
        """
        if not self.converting:
            self.converting = True
            self.progress_bar.display = True

        self.progress_bar.update(progress=progress)
        if message:
            self.progress_label.update(message)
