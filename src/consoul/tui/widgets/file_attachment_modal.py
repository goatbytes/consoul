"""File attachment modal with directory tree navigation and multi-select.

This module provides a modal dialog for selecting files to attach to messages.
Uses Textual's DirectoryTree for navigation with multi-select support via Space key.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Label
from textual.widgets._directory_tree import DirEntry

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.widgets._tree import TreeNode

logger = logging.getLogger(__name__)

__all__ = ["FileAttachmentModal"]


class FileAttachmentModal(ModalScreen[list[str]]):
    """Modal for selecting files to attach using directory tree navigation.

    Features:
    - Navigate directory tree with arrow keys
    - Space to select/deselect files
    - Enter to confirm selection
    - Shows count of selected files
    - Returns list of selected file paths

    Keyboard shortcuts:
    - Space: Toggle file selection
    - Enter: Confirm and close
    - Escape: Cancel

    Example:
        >>> def on_mount(self):
        ...     self.push_screen(FileAttachmentModal(), callback=self.handle_files)
        ...
        ... def handle_files(self, file_paths: list[str] | None):
        ...     if file_paths:
        ...         print(f"Selected {len(file_paths)} files")
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "confirm", "Confirm", show=True),
        Binding("space", "toggle_selection", "Select", show=True),
    ]

    DEFAULT_CSS = """
    FileAttachmentModal {
        align: center middle;
    }

    FileAttachmentModal > Vertical {
        width: 90;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 0;
    }

    FileAttachmentModal #modal-header {
        width: 100%;
        height: auto;
        padding: 1 2;
        background: $primary;
        color: $text;
        text-style: bold;
    }

    FileAttachmentModal #help-text {
        width: 100%;
        height: auto;
        padding: 1 2;
        color: $text-muted;
        background: $surface-lighten-1;
    }

    FileAttachmentModal #nav-buttons {
        width: 100%;
        height: auto;
        padding: 1 2;
        align: center middle;
        background: $surface;
    }

    FileAttachmentModal #nav-buttons Button {
        margin: 0 1;
        min-width: 10;
    }

    FileAttachmentModal #tree-container {
        width: 100%;
        height: auto;
        min-height: 20;
        max-height: 40;
        padding: 1;
    }

    FileAttachmentModal DirectoryTree {
        width: 100%;
        height: 100%;
        background: $panel;
        border: round $accent;
        scrollbar-size: 1 1;
    }

    FileAttachmentModal DirectoryTree:focus {
        border: round $primary;
    }

    FileAttachmentModal #selected-files-container {
        width: 100%;
        height: auto;
        # max-height: 8;
        padding: 1 2;
        background: $surface-darken-1;
        border-top: solid $accent;
    }

    FileAttachmentModal #selected-files-label {
        width: 100%;
        height: auto;
        color: $accent;
        text-style: bold;
        padding-bottom: 1;
    }

    FileAttachmentModal #selected-files-scroll {
        width: 100%;
        height: auto;
        max-height: 5;
    }

    FileAttachmentModal .selected-file-item {
        width: 100%;
        height: auto;
        color: $text-muted;
        padding: 0 1;
    }

    FileAttachmentModal #modal-footer {
        width: 100%;
        height: auto;
        # padding: 1 2;
        align: right middle;
        background: $surface;
        border-top: solid $primary;
    }

    FileAttachmentModal #modal-footer Button {
        margin-left: 1;
        margin-right: 1;
    }
    """

    def __init__(self, start_path: str | Path | None = None) -> None:
        """Initialize file attachment modal.

        Args:
            start_path: Starting directory path (defaults to root for full navigation)
        """
        super().__init__()
        # Start at root for full navigation capability
        self.start_path = Path.cwd()
        self.cwd = Path(start_path) if start_path else Path.cwd()
        self.selected_files: set[Path] = set()

    def compose(self) -> ComposeResult:
        """Compose the modal layout.

        Yields:
            Vertical container with header, navigation buttons, directory tree, selected files display, and footer
        """
        with Vertical():
            yield Label("Select Files to Attach", id="modal-header")

            yield Label(
                "[dim]Navigate:[/dim] [i]↑↓[/i]  [dim]Select:[/dim] [i]Space[/i] [dim]Open/Close/Confirm:[/dim] [i]Enter[/i] [dim]Cancel:[/dim] [i]Esc[/i]",
                id="help-text",
            )

            # Quick navigation buttons
            with Horizontal(id="nav-buttons"):
                yield Button("⛭ Root", id="nav-root", variant="default")
                yield Button("⌂ Home", id="nav-home", variant="default")
                yield Button("⟂ CWD", id="nav-cwd", variant="default")
                yield Button("⤒ Up", id="nav-parent", variant="default")

            with Vertical(id="tree-container"):
                yield DirectoryTree(str(self.start_path), id="file-tree")

            with Vertical(id="selected-files-container"):
                yield Label(
                    f"Selected Files: {len(self.selected_files)}",
                    id="selected-files-label",
                )
                with VerticalScroll(id="selected-files-scroll"):
                    pass

            with Horizontal(id="modal-footer"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button(
                    f"Attach {len(self.selected_files)} File(s)",
                    variant="primary",
                    id="confirm-btn",
                )

    def on_mount(self) -> None:
        """Focus the directory tree on mount."""
        tree = self.query_one("#file-tree", DirectoryTree)
        tree.focus()

    def action_toggle_selection(self) -> None:
        """Toggle selection of currently highlighted file."""
        tree = self.query_one("#file-tree", DirectoryTree)

        if tree.cursor_node is None:
            return

        # Get the path from the cursor node
        node_data = tree.cursor_node.data
        if node_data is None:
            return

        # Extract Path from DirEntry
        file_path = node_data.path if isinstance(node_data, DirEntry) else node_data

        # Only allow selecting files, not directories
        if not file_path.is_file():
            self.app.notify(
                "Can only select files, not directories", severity="warning"
            )
            return

        # Toggle selection
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
            logger.debug(f"Deselected: {file_path}")
        else:
            self.selected_files.add(file_path)
            logger.debug(f"Selected: {file_path}")

        # Update display
        self._update_selected_files_display()
        self._update_tree_node_style(tree.cursor_node)

    def action_confirm(self) -> None:
        """Confirm selection and close modal with selected files."""
        file_paths = [str(path) for path in sorted(self.selected_files)]
        logger.info(f"Confirmed {len(file_paths)} file(s) selected")
        self.dismiss(file_paths)

    def action_cancel(self) -> None:
        """Cancel and close modal without selection."""
        logger.debug("File selection cancelled")
        self.dismiss([])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        # Navigation buttons
        if button_id == "nav-home":
            self._navigate_to(Path.home())
        elif button_id == "nav-cwd":
            self._navigate_to(self.cwd)
        elif button_id == "nav-root":
            self._navigate_to(Path("/"))
        elif button_id == "nav-parent":
            tree = self.query_one("#file-tree", DirectoryTree)
            current = Path(tree.path)
            if current.parent != current:  # Not at root
                self._navigate_to(current.parent)
        # Modal action buttons
        elif button_id == "cancel-btn":
            self.action_cancel()
        elif button_id == "confirm-btn":
            self.action_confirm()

    def _navigate_to(self, path: Path) -> None:
        """Navigate the directory tree to a specific path.

        Args:
            path: Path to navigate to
        """
        tree = self.query_one("#file-tree", DirectoryTree)
        tree.path = path

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection from DirectoryTree (Enter key on a file).

        Instead of dismissing immediately, toggle selection like Space does.

        Args:
            event: File selected event from DirectoryTree
        """
        event.stop()  # Prevent default handling
        self.action_toggle_selection()

    def _update_selected_files_display(self) -> None:
        """Update the selected files display area."""
        # Update count label
        label = self.query_one("#selected-files-label", Label)
        count = len(self.selected_files)
        label.update(f"Selected Files: {count}")

        # Update confirm button text
        confirm_btn = self.query_one("#confirm-btn", Button)
        confirm_btn.label = f"Attach {count} File(s)"

        # Update file list
        scroll = self.query_one("#selected-files-scroll", VerticalScroll)
        scroll.remove_children()

        if not self.selected_files:
            scroll.mount(Label("No files selected", classes="selected-file-item"))
        else:
            for file_path in sorted(self.selected_files):
                scroll.mount(Label(f"• {file_path.name}", classes="selected-file-item"))

    def _update_tree_node_style(self, node: TreeNode[DirEntry]) -> None:
        """Update visual style of tree node based on selection status.

        Args:
            node: Tree node to update
        """
        if node.data is None:
            return

        # Extract Path from DirEntry
        file_path = node.data.path if isinstance(node.data, DirEntry) else node.data

        if not file_path.is_file():
            return

        # Update node label to show selection
        tree = self.query_one("#file-tree", DirectoryTree)
        if file_path in self.selected_files:
            # Add checkmark for selected files
            node.set_label(f"✓ {file_path.name}")
        else:
            # Remove checkmark
            node.set_label(file_path.name)

        tree.refresh()
