"""PermissionManagerScreen - Modal dialog for managing tool permissions.

Provides a visual interface for:
- Switching between permission policies (PARANOID/BALANCED/TRUSTING/UNRESTRICTED)
- Managing whitelist patterns (add/remove)
- Viewing blocklist patterns (read-only)
- Persisting changes to configuration
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Select,
    Static,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.config import ConsoulConfig

__all__ = ["AddPatternModal", "PermissionManagerScreen"]


class AddPatternModal(ModalScreen[tuple[str, str, str] | None]):
    """Modal for adding new whitelist patterns.

    Returns tuple of (pattern, pattern_type, description) or None if cancelled.
    """

    DEFAULT_CSS = """
    AddPatternModal {
        align: center middle;
    }

    AddPatternModal > Vertical {
        width: 70;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    AddPatternModal .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
    }

    AddPatternModal .field-label {
        width: 100%;
        color: $text;
        margin: 1 0 0 0;
    }

    AddPatternModal Input {
        width: 100%;
        margin: 0 0 1 0;
    }

    AddPatternModal RadioSet {
        width: 100%;
        height: auto;
        background: transparent;
        border: none;
        padding: 0;
        margin: 0 0 1 0;
    }

    AddPatternModal RadioButton {
        width: 100%;
        background: transparent;
        margin: 0;
        padding: 0 1;
    }

    AddPatternModal .validation-error {
        width: 100%;
        color: $error;
        text-align: center;
        margin: 0 0 1 0;
        min-height: 1;
    }

    AddPatternModal .button-container {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin: 1 0 0 0;
    }

    AddPatternModal Button {
        min-width: 16;
        margin: 0 1;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize add pattern modal."""
        super().__init__(**kwargs)
        self.pattern_value = ""
        self.pattern_type_value = "exact"
        self.description_value = ""

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical():
            yield Label("Add Whitelist Pattern", classes="modal-title")

            yield Label("Pattern (command or regex):", classes="field-label")
            yield Input(
                placeholder="e.g., git status or git.*",
                id="pattern-input",
            )

            yield Label("Pattern Type:", classes="field-label")
            with RadioSet(id="pattern-type"):
                yield RadioButton("Exact match", value=True, id="type-exact")
                yield RadioButton("Regular expression", id="type-regex")

            yield Label("Description (optional):", classes="field-label")
            yield Input(
                placeholder="e.g., Read-only git commands",
                id="description-input",
            )

            yield Static("", classes="validation-error", id="error-label")

            with Horizontal(classes="button-container"):
                yield Button("Add", variant="success", id="add-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add-button":
            await self._handle_add()
        elif event.button.id == "cancel-button":
            self.dismiss(None)

    async def _handle_add(self) -> None:
        """Validate and add pattern."""
        pattern_input = self.query_one("#pattern-input", Input)
        description_input = self.query_one("#description-input", Input)
        error_label = self.query_one("#error-label", Static)

        pattern = pattern_input.value.strip()
        description = description_input.value.strip()

        # Determine pattern type
        type_exact_button = self.query_one("#type-exact", RadioButton)
        pattern_type = "exact" if type_exact_button.value else "regex"

        # Validate
        if not pattern:
            error_label.update("❌ Pattern cannot be empty")
            return

        if pattern_type == "regex":
            try:
                re.compile(pattern)
            except re.error as e:
                error_label.update(f"❌ Invalid regex: {e}")
                return

        # Success - return the pattern info
        self.dismiss((pattern, pattern_type, description))

    def action_cancel(self) -> None:
        """Cancel action (ESC key)."""
        self.dismiss(None)


class PermissionManagerScreen(ModalScreen[bool]):
    """Modal screen for managing tool execution permissions.

    Provides interface for:
    - Selecting permission policy (PARANOID/BALANCED/TRUSTING/UNRESTRICTED)
    - Managing whitelist patterns
    - Viewing blocklist patterns
    - Persisting configuration changes
    """

    DEFAULT_CSS = """
    PermissionManagerScreen {
        align: center middle;
    }

    PermissionManagerScreen > Vertical {
        width: 100;
        height: auto;
        max-height: 95%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    PermissionManagerScreen .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
    }

    PermissionManagerScreen .section-title {
        width: 100%;
        text-style: bold;
        color: $accent;
        margin: 1 0 0 0;
    }

    PermissionManagerScreen .policy-description {
        width: 100%;
        color: $text-muted;
        margin: 0 0 1 0;
        text-align: center;
    }

    PermissionManagerScreen Select {
        width: 100%;
        margin: 0 0 1 0;
    }

    PermissionManagerScreen DataTable {
        width: 100%;
        height: 12;
        margin: 0 0 1 0;
    }

    PermissionManagerScreen .blocklist-table {
        height: 8;
    }

    PermissionManagerScreen .button-row {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
        margin: 0 0 1 0;
    }

    PermissionManagerScreen .button-row Button {
        margin: 0 1;
    }

    PermissionManagerScreen .main-button-container {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin: 1 0 0 0;
    }

    PermissionManagerScreen .main-button-container Button {
        min-width: 16;
        margin: 0 1;
    }

    PermissionManagerScreen .help-text {
        width: 100%;
        color: $text-muted;
        text-style: italic;
        margin: 1 0 0 0;
        text-align: center;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("ctrl+a", "add_pattern", "Add Pattern", show=False),
        Binding("delete", "remove_pattern", "Remove", show=False),
        Binding("ctrl+s", "apply", "Save", show=False),
    ]

    def __init__(self, config: ConsoulConfig, **kwargs: Any) -> None:
        """Initialize permission manager screen.

        Args:
            config: Full Consoul configuration
            **kwargs: Additional arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.config = config
        self.original_policy = config.tools.permission_policy

        # Initialize whitelist manager
        from consoul.ai.tools.permissions.whitelist import WhitelistManager

        self.whitelist_manager = WhitelistManager()

        # Track selected row in whitelist table
        self.selected_whitelist_row: int | None = None

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        from consoul.ai.tools.permissions.policy import PermissionPolicy

        with Vertical():
            yield Label("🔐 Permission Manager", classes="modal-title")

            # Policy section
            yield Label("Security Policy", classes="section-title")

            # Policy selector
            policy_options = [
                ("PARANOID - Maximum security", PermissionPolicy.PARANOID),
                ("BALANCED - Recommended default", PermissionPolicy.BALANCED),
                ("TRUSTING - Convenience", PermissionPolicy.TRUSTING),
                (
                    "UNRESTRICTED - Testing only (DANGEROUS)",
                    PermissionPolicy.UNRESTRICTED,
                ),
            ]

            yield Select(
                policy_options,
                value=self.config.tools.permission_policy,
                id="policy-selector",
            )

            # Policy description (reactive)
            yield Static(
                self._get_policy_description(self.config.tools.permission_policy),
                classes="policy-description",
                id="policy-description",
            )

            # Whitelist section
            yield Label("Whitelist Patterns", classes="section-title")

            whitelist_table = DataTable(id="whitelist-table", cursor_type="row")
            whitelist_table.add_columns("Pattern", "Type", "Description")
            yield whitelist_table

            # Whitelist buttons
            with Horizontal(classes="button-row"):
                yield Button("+ Add Pattern", id="add-pattern-button")
                yield Button("- Remove Selected", id="remove-pattern-button")

            # Blocklist section
            yield Label("Blocklist Patterns (Read-only)", classes="section-title")

            blocklist_table = DataTable(
                id="blocklist-table",
                cursor_type="none",
                classes="blocklist-table",
            )
            blocklist_table.add_column("Pattern", width=60)
            yield blocklist_table

            # Main action buttons
            with Horizontal(classes="main-button-container"):
                yield Button("Apply", variant="success", id="apply-button")
                yield Button("Cancel", variant="default", id="cancel-button")
                yield Button("Help", variant="primary", id="help-button")

            # Help text
            yield Label(
                "Ctrl+A: Add pattern  |  Delete: Remove  |  Ctrl+S: Save  |  Esc: Cancel",
                classes="help-text",
            )

    def on_mount(self) -> None:
        """Populate tables when screen is mounted."""
        self._populate_whitelist_table()
        self._populate_blocklist_table()

    def _populate_whitelist_table(self) -> None:
        """Populate whitelist table with current patterns."""
        table = self.query_one("#whitelist-table", DataTable)
        table.clear()

        for pattern in self.whitelist_manager.get_patterns():
            table.add_row(
                pattern.pattern,
                pattern.pattern_type,
                pattern.description or "",
            )

    def _populate_blocklist_table(self) -> None:
        """Populate blocklist table with patterns from config."""
        table = self.query_one("#blocklist-table", DataTable)
        table.clear()

        for pattern in self.config.tools.bash.blocked_patterns:
            table.add_row(pattern)

    def _get_policy_description(self, policy: Any) -> str:
        """Get description for a policy."""
        from consoul.ai.tools.permissions.policy import PermissionPolicy

        descriptions = {
            PermissionPolicy.PARANOID: "Approve every command individually. Maximum security.",
            PermissionPolicy.BALANCED: "Auto-approve SAFE commands only. Recommended default.",
            PermissionPolicy.TRUSTING: "Auto-approve SAFE and CAUTION commands. Convenience-focused.",
            PermissionPolicy.UNRESTRICTED: "Auto-approve all commands except BLOCKED. DANGEROUS - testing only!",
        }
        return descriptions.get(policy, "")

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle policy selector changes."""
        from consoul.ai.tools.permissions.policy import PermissionPolicy

        if event.select.id == "policy-selector":
            new_policy = event.value

            # Show confirmation for UNRESTRICTED
            if new_policy == PermissionPolicy.UNRESTRICTED:
                confirmed = await self._confirm_unrestricted_policy()
                if not confirmed:
                    # Reset to previous policy
                    event.select.value = self.config.tools.permission_policy
                    return

            # Update config
            self.config.tools.permission_policy = new_policy

            # Update description
            description = self.query_one("#policy-description", Static)
            description.update(self._get_policy_description(new_policy))

    async def _confirm_unrestricted_policy(self) -> bool:
        """Show confirmation modal for UNRESTRICTED policy."""
        # For now, just return True (will add proper confirmation modal later)
        # TODO: Create proper confirmation modal
        self.app.notify(
            "⚠️  UNRESTRICTED policy enabled. Use with extreme caution!",
            severity="warning",
            timeout=5,
        )
        return True

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add-pattern-button":
            self.action_add_pattern()
        elif event.button.id == "remove-pattern-button":
            await self.action_remove_pattern()
        elif event.button.id == "apply-button":
            await self.action_apply()
        elif event.button.id == "cancel-button":
            self.action_cancel()
        elif event.button.id == "help-button":
            self.action_help()

    def action_add_pattern(self) -> None:
        """Show modal to add new whitelist pattern."""

        def handle_result(result: tuple[str, str, str] | None) -> None:
            """Handle the result from AddPatternModal."""
            if result:
                pattern, pattern_type, description = result

                try:
                    # Type assertion for mypy - pattern_type is validated in modal
                    from typing import Literal, cast

                    self.whitelist_manager.add_pattern(
                        pattern=pattern,
                        pattern_type=cast("Literal['exact', 'regex']", pattern_type),
                        description=description,
                    )
                    self._populate_whitelist_table()
                    self.app.notify(
                        f"✅ Added pattern: {pattern}", severity="information"
                    )
                except ValueError as e:
                    self.app.notify(f"❌ Error: {e}", severity="error")

        self.app.push_screen(AddPatternModal(), handle_result)

    async def action_remove_pattern(self) -> None:
        """Remove selected whitelist pattern."""
        table = self.query_one("#whitelist-table", DataTable)

        # Check if table has any rows
        if table.row_count == 0:
            self.app.notify("No patterns to remove", severity="warning")
            return

        if table.cursor_row is None or table.cursor_row < 0:
            self.app.notify("No pattern selected", severity="warning")
            return

        # Get pattern from selected row
        row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key
        cell = table.get_cell(row_key, "Pattern")
        pattern = str(cell)

        # Remove from manager
        try:
            self.whitelist_manager.remove_pattern(pattern)
            self._populate_whitelist_table()
            self.app.notify(f"✅ Removed pattern: {pattern}", severity="information")
        except ValueError as e:
            self.app.notify(f"❌ Error: {e}", severity="error")

    async def action_apply(self) -> None:
        """Apply changes and save configuration."""
        try:
            # Save whitelist
            self.whitelist_manager.save()

            # Save config to global config path
            from pathlib import Path

            from consoul.config.loader import save_config

            global_config_path = Path.home() / ".consoul" / "config.yaml"
            save_config(self.config, global_config_path)

            self.app.notify(
                "✅ Permission settings saved successfully",
                severity="information",
            )
            self.dismiss(True)
        except Exception as e:
            self.app.notify(f"❌ Error saving configuration: {e}", severity="error")

    def action_cancel(self) -> None:
        """Cancel and discard changes."""
        # Restore original policy
        self.config.tools.permission_policy = self.original_policy
        self.dismiss(False)

    def action_help(self) -> None:
        """Show help information."""
        help_message = (
            "Permission Manager Help:\n\n"
            "PARANOID: Approve every command individually\n"
            "BALANCED: Auto-approve SAFE commands only (recommended)\n"
            "TRUSTING: Auto-approve SAFE and CAUTION commands\n"
            "UNRESTRICTED: Auto-approve all commands (DANGEROUS)\n\n"
            "Whitelist: Add exact matches or regex patterns to bypass approval\n"
            "Blocklist: Always blocked (edit config file to modify)\n\n"
            "Shortcuts: Ctrl+A (add), Delete (remove), Ctrl+S (save), Esc (cancel)"
        )
        self.app.notify(help_message, severity="information", timeout=10)
