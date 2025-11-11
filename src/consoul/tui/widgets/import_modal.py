"""ImportModal - Modal dialog for importing conversations."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.ai.database import ConversationDatabase

__all__ = ["ImportModal"]


class ImportModal(ModalScreen[bool]):
    """Modal dialog for importing conversations from JSON export files.

    Allows user to:
    - Select a JSON export file
    - View preview of conversations to be imported
    - See validation status
    - Import conversations with progress tracking
    """

    DEFAULT_CSS = """
    ImportModal {
        align: center middle;
    }

    ImportModal > Vertical {
        width: 70;
        height: auto;
        max-height: 90%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    ImportModal .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
    }

    ImportModal .section-title {
        width: 100%;
        text-style: bold;
        color: $accent;
        margin: 1 0 0 0;
    }

    ImportModal Input {
        width: 100%;
        margin: 0 0 1 0;
    }

    ImportModal .preview-container {
        width: 100%;
        height: auto;
        max-height: 15;
        background: $surface;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
        overflow-y: auto;
    }

    ImportModal .preview-text {
        width: 100%;
        color: $text;
    }

    ImportModal .progress-label {
        width: 100%;
        color: $accent;
        text-align: center;
        margin: 1 0;
        min-height: 1;
    }

    ImportModal .button-container {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin: 1 0 0 0;
    }

    ImportModal Button {
        min-width: 16;
        margin: 0 1;
    }

    ImportModal .import-button {
        background: $accent;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, db: ConversationDatabase, **kwargs: Any) -> None:
        """Initialize import modal.

        Args:
            db: Database instance
            **kwargs: Additional arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.db = db
        self._importing = False
        self._validated_data: dict[str, Any] | None = None

    def compose(self) -> ComposeResult:
        """Compose the import modal layout."""
        with Vertical():
            yield Label("Import Conversations", classes="modal-title")

            # File path input
            yield Label("JSON Export File:", classes="section-title")
            default_path = Path.home() / "Downloads" / "consoul_export.json"
            yield Input(
                value=str(default_path),
                placeholder="Enter path to JSON export file...",
                id="filepath-input",
            )

            # Validate button
            yield Button("Validate File", variant="default", id="validate-button")

            # Preview container
            yield Label("Preview:", classes="section-title")
            with Vertical(classes="preview-container", id="preview-container"):
                yield Static(
                    "Select a file and click Validate to preview",
                    classes="preview-text",
                    id="preview-text",
                )

            # Progress label
            yield Static("", id="progress-label", classes="progress-label")

            # Buttons
            with Horizontal(classes="button-container"):
                yield Button(
                    "Import",
                    variant="primary",
                    id="import-button",
                    disabled=True,
                )
                yield Button("Cancel", variant="default", id="cancel-button")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-button":
            self.dismiss(False)
        elif event.button.id == "validate-button":
            await self._validate_file()
        elif event.button.id == "import-button" and not self._importing:
            await self._perform_import()

    def action_cancel(self) -> None:
        """Cancel the modal."""
        if not self._importing:
            self.dismiss(False)

    async def _validate_file(self) -> None:
        """Validate the selected import file."""
        try:
            filepath_input = self.query_one("#filepath-input", Input)
            preview_text = self.query_one("#preview-text", Static)
            import_button = self.query_one("#import-button", Button)
            progress_label = self.query_one("#progress-label", Static)

            filepath = Path(filepath_input.value).expanduser()

            if not filepath.exists():
                preview_text.update(f"✗ Error: File not found: {filepath}")
                import_button.disabled = True
                self._validated_data = None
                return

            # Read and parse JSON
            progress_label.update("Reading file...")
            await asyncio.sleep(0)

            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                preview_text.update(f"✗ Error: Invalid JSON file\n{e}")
                import_button.disabled = True
                self._validated_data = None
                progress_label.update("")
                return

            # Validate structure
            progress_label.update("Validating structure...")
            await asyncio.sleep(0)

            from consoul.formatters.json_formatter import JSONFormatter

            try:
                JSONFormatter.validate_import_data(data)
            except ValueError as e:
                preview_text.update(f"✗ Error: Invalid export format\n{e}")
                import_button.disabled = True
                self._validated_data = None
                progress_label.update("")
                return

            # Build preview
            version = data["version"]
            is_multi = version == JSONFormatter.VERSION_MULTI

            preview_lines = [
                "✓ Valid Consoul export file",
                "",
                f"Version: {version}",
                f"Exported: {data['exported_at']}",
                "",
            ]

            if is_multi:
                conversations = data["conversations"]
                preview_lines.append(f"Conversations: {len(conversations)}")
                preview_lines.append("")

                # Show first 10 conversations
                for i, conv_data in enumerate(conversations[:10]):
                    conv = conv_data["conversation"]
                    msg_count = len(conv_data["messages"])
                    preview_lines.append(
                        f"  [{i + 1}] {conv['session_id'][:16]}... - "
                        f"{conv['model']} - {msg_count} messages"
                    )

                if len(conversations) > 10:
                    preview_lines.append(f"  ... and {len(conversations) - 10} more")
            else:
                conv = data["conversation"]
                msg_count = len(data["messages"])
                preview_lines.append(f"Session ID: {conv['session_id']}")
                preview_lines.append(f"Model: {conv['model']}")
                preview_lines.append(f"Messages: {msg_count}")

            preview_text.update("\n".join(preview_lines))
            import_button.disabled = False
            self._validated_data = data
            progress_label.update("✓ Ready to import")

        except Exception as e:
            preview_text = self.query_one("#preview-text", Static)
            import_button = self.query_one("#import-button", Button)
            progress_label = self.query_one("#progress-label", Static)

            preview_text.update(f"✗ Error: {e}")
            import_button.disabled = True
            self._validated_data = None
            progress_label.update("")

    async def _perform_import(self) -> None:
        """Perform the import operation."""
        if not self._validated_data:
            return

        self._importing = True

        try:
            # Disable buttons during import
            import_btn = self.query_one("#import-button", Button)
            cancel_btn = self.query_one("#cancel-button", Button)
            validate_btn = self.query_one("#validate-button", Button)
            import_btn.disabled = True
            cancel_btn.disabled = True
            validate_btn.disabled = True

            progress_label = self.query_one("#progress-label", Static)
            data = self._validated_data

            from consoul.formatters.json_formatter import JSONFormatter

            version = data["version"]
            is_multi = version == JSONFormatter.VERSION_MULTI
            imported_count = 0
            skipped_count = 0

            if is_multi:
                conversations = data["conversations"]
                total = len(conversations)

                for i, conv_data in enumerate(conversations):
                    progress_label.update(f"Importing {i + 1} of {total}...")
                    await asyncio.sleep(0)

                    conv = conv_data["conversation"]
                    session_id = conv["session_id"]

                    # Check if conversation already exists
                    try:
                        self.db.get_conversation_metadata(session_id)
                        skipped_count += 1
                        continue
                    except Exception:
                        # Conversation doesn't exist, proceed with import
                        pass

                    # Create conversation
                    self.db.create_conversation(
                        model=conv["model"], session_id=session_id
                    )

                    # Import messages
                    for msg in conv_data["messages"]:
                        self.db.save_message(
                            session_id=session_id,
                            role=msg["role"],
                            content=msg["content"],
                            tokens=msg.get("tokens"),
                        )

                    imported_count += 1

                # Show results
                result_msg = f"✓ Imported {imported_count} conversations"
                if skipped_count > 0:
                    result_msg += f" ({skipped_count} skipped - already exist)"
                progress_label.update(result_msg)
            else:
                # Single conversation import
                progress_label.update("Importing conversation...")
                await asyncio.sleep(0)

                conv = data["conversation"]
                session_id = conv["session_id"]

                # Check if conversation already exists
                try:
                    self.db.get_conversation_metadata(session_id)
                    progress_label.update(
                        "✗ Conversation already exists (skipped import)"
                    )
                    await asyncio.sleep(2)
                    self.dismiss(False)
                    return
                except Exception:
                    # Conversation doesn't exist, proceed with import
                    pass

                # Create conversation
                self.db.create_conversation(model=conv["model"], session_id=session_id)

                # Import messages
                for msg in data["messages"]:
                    self.db.save_message(
                        session_id=session_id,
                        role=msg["role"],
                        content=msg["content"],
                        tokens=msg.get("tokens"),
                    )

                imported_count = 1
                progress_label.update("✓ Imported 1 conversation")

            # Wait a moment to show success message
            await asyncio.sleep(1.5)

            # Dismiss with success
            self.dismiss(True)

        except Exception as e:
            # Show error
            progress_label = self.query_one("#progress-label", Static)
            progress_label.update(f"✗ Error: {e}")

            # Re-enable buttons
            import_btn = self.query_one("#import-button", Button)
            cancel_btn = self.query_one("#cancel-button", Button)
            validate_btn = self.query_one("#validate-button", Button)
            import_btn.disabled = False
            cancel_btn.disabled = False
            validate_btn.disabled = False

            self._importing = False
