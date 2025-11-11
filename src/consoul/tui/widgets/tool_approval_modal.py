"""ToolApprovalModal - Modal dialog for tool execution approval."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.ai.tools.approval import ToolApprovalRequest

__all__ = ["ToolApprovalModal"]


class ToolApprovalModal(ModalScreen[bool]):
    """Modal dialog for tool execution approval.

    Displays tool information with risk-based color coding and allows
    user to approve or deny execution via buttons or keyboard shortcuts.

    Keyboard Shortcuts:
        - Y: Approve execution
        - N: Deny execution
        - Esc: Deny execution
        - Enter: Approve execution (when focused on approve button)

    Args:
        request: ToolApprovalRequest with tool information
    """

    DEFAULT_CSS = """
    ToolApprovalModal {
        align: center middle;
    }

    ToolApprovalModal > Vertical {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $panel;
        padding: 1 2;
    }

    /* Risk-based border colors */
    ToolApprovalModal.safe > Vertical {
        border: thick $success;
    }

    ToolApprovalModal.caution > Vertical {
        border: thick $warning;
    }

    ToolApprovalModal.dangerous > Vertical {
        border: thick $error;
    }

    ToolApprovalModal .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
    }

    ToolApprovalModal .tool-name {
        width: 100%;
        content-align: center middle;
        text-style: bold italic;
        color: $accent;
        margin: 0 0 1 0;
    }

    ToolApprovalModal .risk-badge {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin: 0 0 1 0;
    }

    ToolApprovalModal .risk-safe {
        color: $success;
    }

    ToolApprovalModal .risk-caution {
        color: $warning;
    }

    ToolApprovalModal .risk-dangerous {
        color: $error;
    }

    ToolApprovalModal .section-title {
        width: 100%;
        text-style: bold;
        color: $accent;
        margin: 1 0 0 0;
    }

    ToolApprovalModal .description {
        width: 100%;
        color: $text-muted;
        margin: 0 0 1 0;
    }

    ToolApprovalModal VerticalScroll {
        width: 100%;
        height: auto;
        max-height: 20;
        border: solid $primary-darken-2;
        background: $surface;
        margin: 0 0 1 0;
        padding: 1;
    }

    ToolApprovalModal .code-block {
        width: 100%;
        color: $text;
        text-style: none;
    }

    ToolApprovalModal .button-container {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin: 1 0 0 0;
    }

    ToolApprovalModal Button {
        min-width: 20;
        margin: 0 1;
    }

    ToolApprovalModal .hint {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        text-style: italic;
        margin: 1 0 0 0;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("y", "approve", "Approve", show=False),
        Binding("n", "deny", "Deny", show=False),
        Binding("escape", "deny", "Deny", show=False),
    ]

    def __init__(
        self,
        request: ToolApprovalRequest,
        **kwargs: Any,
    ) -> None:
        """Initialize tool approval modal.

        Args:
            request: ToolApprovalRequest with tool information
            **kwargs: Additional arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.request = request

        # Add risk-level class for styling
        self.add_class(request.risk_level.value)

    def compose(self) -> ComposeResult:
        """Compose the approval modal layout."""
        with Vertical():
            yield Label("Tool Execution Request", classes="modal-title")
            yield Label(self.request.tool_name, classes="tool-name")

            # Risk level badge
            risk_level = self.request.risk_level.value.upper()
            risk_class = f"risk-{self.request.risk_level.value}"
            yield Label(
                f"⚠  Risk Level: {risk_level}", classes=f"risk-badge {risk_class}"
            )

            # Description if provided
            if self.request.description:
                yield Label("Description", classes="section-title")
                yield Static(self.request.description, classes="description")

            # Arguments section
            if self.request.arguments:
                yield Label("Arguments", classes="section-title")
                with VerticalScroll():
                    yield Static(
                        self._format_arguments(self.request.arguments),
                        classes="code-block",
                    )

            # Buttons
            with Horizontal(classes="button-container"):
                yield Button("Approve (Y)", variant="success", id="approve-button")
                yield Button("Deny (N)", variant="error", id="deny-button")

            # Keyboard hint
            yield Label("Press Y to approve, N or Esc to deny", classes="hint")

    def _format_arguments(self, arguments: dict[str, Any]) -> str:
        """Format arguments as readable JSON.

        Args:
            arguments: Tool arguments dictionary

        Returns:
            Formatted JSON string
        """
        try:
            return json.dumps(arguments, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            # Fallback to repr if JSON serialization fails
            return repr(arguments)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "approve-button":
            self.dismiss(True)
        elif event.button.id == "deny-button":
            self.dismiss(False)

    def action_approve(self) -> None:
        """Approve tool execution (Y key)."""
        self.dismiss(True)

    def action_deny(self) -> None:
        """Deny tool execution (N/Esc key)."""
        self.dismiss(False)
