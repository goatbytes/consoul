"""ExportModal - Modal dialog for exporting conversations."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.ai.database import ConversationDatabase

__all__ = ["ExportModal"]


class ExportModal(ModalScreen[str | None]):
    """Modal dialog for exporting conversations.

    Allows user to:
    - Select export format (JSON, Markdown, HTML, CSV)
    - Choose scope (current conversation or all conversations)
    - Specify output file path
    - See progress during export
    """

    DEFAULT_CSS = """
    ExportModal {
        align: center middle;
    }

    ExportModal > Vertical {
        width: 70;
        height: auto;
        max-height: 90%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    ExportModal .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
    }

    ExportModal .section-title {
        width: 100%;
        text-style: bold;
        color: $accent;
        margin: 1 0 0 0;
    }

    ExportModal RadioSet {
        width: 100%;
        height: auto;
        background: transparent;
        border: none;
        padding: 0;
    }

    ExportModal RadioButton {
        width: 100%;
        background: transparent;
        margin: 0;
        padding: 0 1;
    }

    ExportModal Input {
        width: 100%;
        margin: 0 0 1 0;
    }

    ExportModal .progress-label {
        width: 100%;
        color: $accent;
        text-align: center;
        margin: 1 0;
        min-height: 1;
    }

    ExportModal .button-container {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin: 1 0 0 0;
    }

    ExportModal Button {
        min-width: 16;
        margin: 0 1;
    }

    ExportModal .export-button {
        background: $accent;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(
        self,
        current_session_id: str | None,
        db: ConversationDatabase,
        **kwargs: Any,
    ) -> None:
        """Initialize export modal.

        Args:
            current_session_id: ID of current conversation (if any)
            db: Database instance
            **kwargs: Additional arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.current_session_id = current_session_id
        self.db = db
        self._exporting = False

    def compose(self) -> ComposeResult:
        """Compose the export modal layout."""
        with Vertical():
            yield Label("Export Conversation", classes="modal-title")

            # Format selection
            yield Label("Format:", classes="section-title")
            with RadioSet(id="format-selector"):
                yield RadioButton("JSON (with metadata)", value=True, id="format-json")
                yield RadioButton("Markdown (human-readable)", id="format-markdown")
                yield RadioButton("HTML (web-friendly)", id="format-html")
                yield RadioButton("CSV (spreadsheet)", id="format-csv")

            # Scope selection
            yield Label("Scope:", classes="section-title")
            with RadioSet(id="scope-selector"):
                if self.current_session_id:
                    yield RadioButton(
                        "Current conversation", value=True, id="scope-current"
                    )
                yield RadioButton(
                    "All conversations",
                    value=not bool(self.current_session_id),
                    id="scope-all",
                )

            # File path input
            yield Label("Output file:", classes="section-title")
            default_path = self._get_default_filepath("json")
            yield Input(
                value=str(default_path),
                placeholder="Enter file path...",
                id="filepath-input",
            )

            # Progress label
            yield Static("", id="progress-label", classes="progress-label")

            # Buttons
            with Horizontal(classes="button-container"):
                yield Button("Export", variant="primary", id="export-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_mount(self) -> None:
        """Initialize modal after mounting."""
        # Disable current conversation option if no active conversation
        if not self.current_session_id:
            try:
                scope_current = self.query_one("#scope-current", RadioButton)
                scope_current.disabled = True
            except Exception:
                pass

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle format selection changes to update file extension."""
        if event.radio_set.id == "format-selector":
            # Get selected format
            format_map = {
                "format-json": "json",
                "format-markdown": "md",
                "format-html": "html",
                "format-csv": "csv",
            }
            selected_format = format_map.get(str(event.pressed.id), "json")

            # Update filepath with new extension
            try:
                filepath_input = self.query_one("#filepath-input", Input)
                current_path = Path(filepath_input.value)
                new_path = current_path.with_suffix(f".{selected_format}")
                filepath_input.value = str(new_path)
            except Exception:
                pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "export-button" and not self._exporting:
            await self._perform_export()

    def action_cancel(self) -> None:
        """Cancel the modal."""
        if not self._exporting:
            self.dismiss(None)

    async def _perform_export(self) -> None:
        """Perform the export operation."""
        self._exporting = True

        try:
            # Disable buttons during export
            export_btn = self.query_one("#export-button", Button)
            cancel_btn = self.query_one("#cancel-button", Button)
            export_btn.disabled = True
            cancel_btn.disabled = True

            # Get selections
            format_selector = self.query_one("#format-selector", RadioSet)
            scope_selector = self.query_one("#scope-selector", RadioSet)
            filepath_input = self.query_one("#filepath-input", Input)

            format_map = {
                "format-json": "json",
                "format-markdown": "markdown",
                "format-html": "html",
                "format-csv": "csv",
            }
            pressed_button = format_selector.pressed_button
            selected_format = format_map.get(
                str(pressed_button.id) if pressed_button is not None else "", "json"
            )
            scope_button = scope_selector.pressed_button
            is_current_scope = (
                scope_button.id == "scope-current"
                if scope_button is not None
                else False
            )

            filepath = Path(filepath_input.value).expanduser()

            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Import formatters
            from consoul.formatters.csv_formatter import CSVFormatter
            from consoul.formatters.html import HTMLFormatter
            from consoul.formatters.json_formatter import JSONFormatter
            from consoul.formatters.markdown import MarkdownFormatter

            formatters = {
                "json": JSONFormatter(),
                "markdown": MarkdownFormatter(),
                "html": HTMLFormatter(),
                "csv": CSVFormatter(),
            }
            formatter = formatters[selected_format]

            progress_label = self.query_one("#progress-label", Static)

            if is_current_scope and self.current_session_id:
                # Export current conversation
                progress_label.update("Exporting conversation...")
                await asyncio.sleep(0)  # Allow UI update

                metadata = self.db.get_conversation_metadata(self.current_session_id)
                messages = self.db.load_conversation(self.current_session_id)
                content = formatter.export(metadata, messages)
                filepath.write_text(content, encoding="utf-8")

                progress_label.update(f"✓ Exported to {filepath.name}")
            else:
                # Export all conversations
                conversations = self.db.list_conversations()
                total = len(conversations)

                if selected_format == "json":
                    # Use multi-conversation JSON format
                    progress_label.update(f"Exporting {total} conversations...")
                    await asyncio.sleep(0)

                    data = []
                    for i, conv in enumerate(conversations):
                        metadata = self.db.get_conversation_metadata(conv["session_id"])
                        messages = self.db.load_conversation(conv["session_id"])
                        data.append((metadata, messages))

                        if (i + 1) % 5 == 0:
                            progress_label.update(
                                f"Loading {i + 1} of {total} conversations..."
                            )
                            await asyncio.sleep(0)

                    content = JSONFormatter.export_multiple(data)
                    filepath.write_text(content, encoding="utf-8")
                    progress_label.update(f"✓ Exported {total} conversations")
                else:
                    # Export each conversation to separate file
                    for i, conv in enumerate(conversations):
                        progress_label.update(f"Exporting {i + 1} of {total}...")
                        await asyncio.sleep(0)

                        metadata = self.db.get_conversation_metadata(conv["session_id"])
                        messages = self.db.load_conversation(conv["session_id"])

                        file_path = (
                            filepath.parent
                            / f"{filepath.stem}_{conv['session_id']}.{formatter.file_extension}"
                        )
                        formatter.export_to_file(metadata, messages, file_path)

                    progress_label.update(
                        f"✓ Exported {total} files to {filepath.parent}"
                    )

            # Wait a moment to show success message
            await asyncio.sleep(1)

            # Dismiss with filepath
            self.dismiss(str(filepath))

        except Exception as e:
            # Show error
            progress_label = self.query_one("#progress-label", Static)
            progress_label.update(f"✗ Error: {e}")

            # Re-enable buttons
            export_btn = self.query_one("#export-button", Button)
            cancel_btn = self.query_one("#cancel-button", Button)
            export_btn.disabled = False
            cancel_btn.disabled = False

            self._exporting = False

    def _get_default_filepath(self, extension: str) -> Path:
        """Get default filepath for export.

        Args:
            extension: File extension (json, md, html, csv)

        Returns:
            Path to default export file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"consoul_export_{timestamp}.{extension}"
        return Path.home() / "Downloads" / filename
