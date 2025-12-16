"""ToolManagerScreen - Modal dialog for managing tool availability.

Provides a visual interface for:
- Viewing all registered tools with descriptions
- Toggling tools on/off at runtime
- Quick filters (All, None, Safe Only)
- Risk level visualization
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.ai.tools.base import ToolMetadata
    from consoul.ai.tools.registry import ToolRegistry

__all__ = ["ToolManagerScreen"]


class ToolManagerScreen(ModalScreen[bool]):
    """Modal screen for managing tool availability at runtime.

    Allows users to:
    - View all registered tools
    - Toggle individual tools on/off
    - Apply quick filters (All/None/Safe Only)
    - See risk levels with color coding
    """

    DEFAULT_CSS = """
    ToolManagerScreen {
        align: center middle;
    }

    ToolManagerScreen > Vertical {
        width: 120;
        height: auto;
        max-height: 95%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    ToolManagerScreen .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
    }

    ToolManagerScreen .tool-count {
        width: 100%;
        content-align: center middle;
        color: $text 60%;
        margin: 0 0 1 0;
        text-align: center;
    }

    ToolManagerScreen DataTable {
        height: 1fr;
        margin: 1 0;
    }

    /* Risk level colors */
    ToolManagerScreen .risk-safe {
        color: $success;
    }

    ToolManagerScreen .risk-caution {
        color: $warning;
    }

    ToolManagerScreen .risk-dangerous {
        color: $error;
    }

    ToolManagerScreen .button-container {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
        margin: 1 0 0 0;
    }

    ToolManagerScreen Button {
        margin: 0 1;
        min-width: 16;
    }

    ToolManagerScreen .filter-container {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
        margin: 0 0 1 0;
    }

    ToolManagerScreen .filter-button {
        margin: 0 1;
        min-width: 12;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape,q", "cancel", "Cancel", show=True),
        Binding("enter", "apply", "Apply", show=True),
        Binding("space", "toggle_tool", "Toggle", show=False),
        Binding("t", "toggle_tool", "Toggle", show=False),
        Binding("a", "filter_all", "All", show=True),
        Binding("n", "filter_none", "None", show=True),
        Binding("s", "filter_safe", "Safe", show=True),
        Binding("ctrl+s", "save_to_config", "Save to Config", show=True),
    ]

    def __init__(
        self,
        tool_registry: ToolRegistry,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize ToolManagerScreen.

        Args:
            tool_registry: The tool registry to manage
            name: The name of the screen
            id: The ID of the screen in the DOM
            classes: The CSS classes for the screen
        """
        super().__init__(name=name, id=id, classes=classes)
        self.tool_registry = tool_registry
        # Track pending changes (tool_name -> enabled state)
        self.pending_changes: dict[str, bool] = {}

    def compose(self) -> ComposeResult:
        """Compose the tool manager layout."""
        with Vertical():
            yield Static("Tool Manager", classes="modal-title")
            yield Static("", classes="tool-count", id="tool-count")
            yield Static(
                "Space/T: toggle · ↑↓: navigate · A: all · N: none · S: safe · Ctrl+S: save to config · Enter: apply · Esc: cancel",
                classes="tool-count",
            )

            # Quick filter buttons
            with Horizontal(classes="filter-container"):
                yield Button(
                    "All (A)",
                    variant="default",
                    classes="filter-button",
                    id="filter-all",
                )
                yield Button(
                    "None (N)",
                    variant="default",
                    classes="filter-button",
                    id="filter-none",
                )
                yield Button(
                    "Safe (S)",
                    variant="default",
                    classes="filter-button",
                    id="filter-safe",
                )

            # Tool list table
            table: DataTable[str] = DataTable(
                id="tool-table", zebra_stripes=True, cursor_type="row"
            )
            yield table

            # Action buttons
            with Horizontal(classes="button-container"):
                yield Button("Cancel (Esc)", variant="default", id="cancel-btn")
                yield Button("Apply (Enter)", variant="primary", id="apply-btn")

    def on_mount(self) -> None:
        """Initialize the tool table when screen mounts."""
        table = self.query_one("#tool-table", DataTable)

        # Add columns
        table.add_columns("", "Tool", "Risk", "Description")

        # Populate table with tools
        tools = self.tool_registry.list_tools()
        for meta in tools:
            self._add_tool_row(table, meta)

        # Update tool count
        self._update_tool_count()

        # Focus the table
        table.focus()

    def _add_tool_row(self, table: DataTable[str], meta: ToolMetadata) -> None:
        """Add a tool row to the table.

        Args:
            table: The DataTable widget
            meta: Tool metadata to add
        """
        # Get current enabled state (pending change or actual)
        enabled = self.pending_changes.get(meta.name, meta.enabled)

        # Checkbox indicator
        checkbox = "✓" if enabled else " "

        # Risk level with color
        risk_text = meta.risk_level.name

        # Truncate description if too long
        desc = meta.description
        if len(desc) > 60:
            desc = desc[:57] + "..."

        # Add row with tool name as key
        table.add_row(checkbox, meta.name, risk_text, desc, key=meta.name)

    def _update_tool_count(self) -> None:
        """Update the tool count display."""
        tools = self.tool_registry.list_tools()
        enabled_count = sum(
            1 for meta in tools if self.pending_changes.get(meta.name, meta.enabled)
        )
        total_count = len(tools)

        count_label = self.query_one("#tool-count", Static)
        count_label.update(f"{total_count} tools ({enabled_count} enabled)")

    def _refresh_table(self, preserve_cursor: bool = True) -> None:
        """Refresh the entire table with current state.

        Args:
            preserve_cursor: If True, restore cursor position after refresh
        """
        table = self.query_one("#tool-table", DataTable)

        # Save cursor position before clearing
        saved_cursor = table.cursor_row if preserve_cursor else None

        table.clear()

        tools = self.tool_registry.list_tools()
        for meta in tools:
            self._add_tool_row(table, meta)

        self._update_tool_count()

        # Restore cursor position
        if saved_cursor is not None and saved_cursor >= 0:
            # If cursor position is invalid, leave it at default
            with contextlib.suppress(Exception):
                table.move_cursor(row=saved_cursor)

    def action_toggle_tool(self) -> None:
        """Toggle the selected tool's enabled state (Space/T key)."""
        table = self.query_one("#tool-table", DataTable)

        cursor_row = table.cursor_row
        if cursor_row is None or cursor_row < 0:
            return

        # Get row key from cursor position
        row_keys = list(table.rows.keys())
        if 0 <= cursor_row < len(row_keys):
            row_key = row_keys[cursor_row]
            # RowKey object has a value property that contains the actual string key
            tool_name = (
                str(row_key.value) if hasattr(row_key, "value") else str(row_key)
            )

            # Get current state
            tools = self.tool_registry.list_tools()
            meta = next((m for m in tools if m.name == tool_name), None)

            if meta:
                # Toggle pending state
                current_state = self.pending_changes.get(tool_name, meta.enabled)
                self.pending_changes[tool_name] = not current_state

                # Refresh display
                self._refresh_table()

    def action_filter_all(self) -> None:
        """Enable all tools."""
        tools = self.tool_registry.list_tools()
        for meta in tools:
            self.pending_changes[meta.name] = True

        self._refresh_table()

    def action_filter_none(self) -> None:
        """Disable all tools."""
        tools = self.tool_registry.list_tools()
        for meta in tools:
            self.pending_changes[meta.name] = False

        self._refresh_table()

    def action_filter_safe(self) -> None:
        """Enable only SAFE tools, disable others."""
        from consoul.ai.tools.base import RiskLevel

        tools = self.tool_registry.list_tools()
        for meta in tools:
            self.pending_changes[meta.name] = meta.risk_level == RiskLevel.SAFE

        self._refresh_table()

    def action_apply(self) -> None:
        """Apply pending changes and close screen."""
        # Apply all pending changes to registry
        for tool_name, enabled in self.pending_changes.items():
            tools = self.tool_registry.list_tools()
            meta = next((m for m in tools if m.name == tool_name), None)
            if meta:
                meta.enabled = enabled

        # Trigger rebind immediately via app to update system prompt
        self.app._rebind_tools()  # type: ignore[attr-defined]

        # Return True to indicate changes were applied
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel changes and close screen."""
        logger.info("[TOOL_MGR] action_cancel called")
        # Return False to indicate no changes
        self.dismiss(False)

    def action_save_to_config(self) -> None:
        """Save current tool selection to config file (Ctrl+S)."""
        from pathlib import Path

        from consoul.config.loader import find_config_files, save_config

        try:
            # Get enabled tools from pending changes (or current state if no changes)
            tools = self.tool_registry.list_tools()
            enabled_tools = [
                meta.name
                for meta in tools
                if self.pending_changes.get(meta.name, meta.enabled)
            ]

            # Determine config file path (prefer project, fallback to global)
            global_config, project_config = find_config_files()
            config_path = project_config or global_config

            # If no config exists, create global config
            if not config_path:
                config_path = Path.home() / ".consoul" / "config.yaml"

            # Get app's config and update allowed_tools
            config = self.app.consoul_config  # type: ignore[attr-defined]
            config.tools.allowed_tools = enabled_tools

            # Save to config file
            save_config(config, config_path)

            # Show confirmation with shortened path
            config_name = (
                "config.yaml"
                if config_path == Path.home() / ".consoul" / "config.yaml"
                else ".consoul/config.yaml"
            )
            self.app.notify(
                f"Tool selection saved to {config_name}",
                severity="information",
            )
            logger.info(f"[TOOL_MGR] Saved {len(enabled_tools)} tools to {config_path}")

        except Exception as e:
            error_msg = str(e).replace("[", "\\[")
            self.app.notify(
                f"Failed to save config: {error_msg}",
                severity="error",
            )
            logger.error(f"[TOOL_MGR] Failed to save config: {e}", exc_info=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: The button press event
        """
        if event.button.id == "apply-btn":
            self.action_apply()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "filter-all":
            self.action_filter_all()
        elif event.button.id == "filter-none":
            self.action_filter_none()
        elif event.button.id == "filter-safe":
            self.action_filter_safe()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key) - no action, use Space for toggle.

        Args:
            event: The row selection event
        """
        # Prevent Enter from doing anything - Space/T is for toggle
        pass
