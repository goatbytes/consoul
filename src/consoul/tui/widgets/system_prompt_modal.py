"""SystemPromptModal - Modal dialog for viewing system prompt.

Provides a visual interface for:
- Viewing the current system prompt for a conversation
- Seeing metadata (profile name, tool count, timestamp)
- Comparing stored vs current prompt
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, RichLog, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["SystemPromptModal"]


class SystemPromptModal(ModalScreen[None]):
    """Modal screen for viewing system prompt and metadata.

    Displays:
    - Full system prompt content (scrollable)
    - Profile name used
    - Tool count at conversation start
    - Timestamp when prompt was stored
    """

    DEFAULT_CSS = """
    SystemPromptModal {
        align: center middle;
    }

    SystemPromptModal > Vertical {
        width: 120;
        height: auto;
        max-height: 95%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    SystemPromptModal .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
    }

    SystemPromptModal .metadata {
        width: 100%;
        color: $text 80%;
        margin: 0 0 1 0;
    }

    SystemPromptModal RichLog {
        height: 1fr;
        margin: 1 0;
        border: solid $primary-lighten-1;
        background: $surface;
    }

    SystemPromptModal .button-container {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
        margin: 1 0 0 0;
    }

    SystemPromptModal Button {
        margin: 0 1;
        min-width: 16;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape,q", "close", "Close", show=True),
    ]

    def __init__(
        self,
        system_prompt: str,
        profile_name: str | None = None,
        tool_count: int | None = None,
        stored_at: str | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize SystemPromptModal.

        Args:
            system_prompt: The system prompt content to display
            profile_name: Name of the profile used (optional)
            tool_count: Number of tools enabled (optional)
            stored_at: Timestamp when prompt was stored (optional)
            name: The name of the screen
            id: The ID of the screen in the DOM
            classes: The CSS classes for the screen
        """
        super().__init__(name=name, id=id, classes=classes)
        self.system_prompt = system_prompt
        self.profile_name = profile_name
        self.tool_count = tool_count
        self.stored_at = stored_at

    def compose(self) -> ComposeResult:
        """Compose the system prompt modal layout."""
        with Vertical():
            yield Static("System Prompt", classes="modal-title")

            # Metadata line
            metadata_parts = []
            if self.profile_name:
                metadata_parts.append(f"Profile: {self.profile_name}")
            if self.tool_count is not None:
                metadata_parts.append(f"Tools: {self.tool_count}")
            if self.stored_at:
                # Format timestamp (just date/time, not microseconds)
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(self.stored_at.replace("Z", "+00:00"))
                    formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
                    metadata_parts.append(f"Stored: {formatted}")
                except Exception:
                    metadata_parts.append(f"Stored: {self.stored_at}")

            if metadata_parts:
                yield Static(" · ".join(metadata_parts), classes="metadata")
            else:
                yield Static("(No metadata available)", classes="metadata")

            # System prompt content
            rich_log = RichLog(id="prompt-content", highlight=True, markup=True)
            yield rich_log

            # Close button
            yield Button("Close (Esc)", variant="primary", id="close-btn")

    def on_mount(self) -> None:
        """Populate the RichLog with system prompt content when screen mounts."""
        rich_log = self.query_one("#prompt-content", RichLog)

        # Display prompt with markdown-style highlighting
        rich_log.write(self.system_prompt)

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: The button press event
        """
        if event.button.id == "close-btn":
            self.action_close()
