"""ToolManagerScreen - Modal dialog for managing tool availability.

Provides a visual interface for:
- Viewing all registered tools with descriptions
- Toggling tools on/off at runtime
- Quick filters (All, None, Safe Only)
- Risk level visualization
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static

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
                "Space/T: toggle · ↑↓: navigate · A: all · N: none · S: safe · Enter: apply · Esc: cancel",
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

    def _refresh_table(self) -> None:
        """Refresh the entire table with current state."""
        table = self.query_one("#tool-table", DataTable)
        table.clear()

        tools = self.tool_registry.list_tools()
        for meta in tools:
            self._add_tool_row(table, meta)

        self._update_tool_count()

    def action_toggle_tool(self) -> None:
        """Toggle the selected tool's enabled state."""
        table = self.query_one("#tool-table", DataTable)

        if table.cursor_row >= 0:
            # Get tool name from row key
            row_key = table.get_row_at(table.cursor_row)
            if row_key:
                tool_name = str(row_key)

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

        # Return True to indicate changes were applied
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel changes and close screen."""
        # Return False to indicate no changes
        self.dismiss(False)

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
