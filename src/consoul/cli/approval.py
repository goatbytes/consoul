"""Enhanced CLI approval provider with session-level approval tracking.

Provides y/n/a/v approval options (yes/no/always/never) for tool execution
in CLI chat sessions. Supports Rich panels for tool call display and tracks
approval decisions at the session level.
"""

from __future__ import annotations

import asyncio
import json

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax

from consoul.ai.tools.approval import ToolApprovalRequest, ToolApprovalResponse


class CliToolApprovalProvider:
    """CLI approval provider with session-level always/never tracking.

    Displays tool information in Rich panels and prompts for approval with
    y/n/a/v options. Tracks "always approve" and "never approve" decisions
    at the session level to avoid repeated prompts for the same tool.

    This provider is used by ChatSession for tool execution approval workflows.

    Example:
        >>> from consoul.cli.approval import CliToolApprovalProvider
        >>> from consoul.ai.tools import ToolRegistry
        >>> from consoul.config.models import ToolConfig
        >>>
        >>> provider = CliToolApprovalProvider()
        >>> config = ToolConfig(enabled=True)
        >>> registry = ToolRegistry(config, approval_provider=provider)
        >>>
        >>> # In chat loop:
        >>> if tool_call['name'] in provider.always_approve:
        ...     approved = True  # Auto-approve
        >>> elif tool_call['name'] in provider.never_approve:
        ...     approved = False  # Auto-deny
        >>> else:
        ...     # Show approval prompt
        ...     response = await provider.request_approval(request)
    """

    def __init__(
        self,
        *,
        console: Console | None = None,
        show_risk_level: bool = True,
        show_preview: bool = True,
    ):
        """Initialize CLI approval provider.

        Args:
            console: Rich console for output. Creates default if None.
            show_risk_level: Whether to display risk level in prompt.
            show_preview: Whether to show diff preview for file operations.
        """
        self.console = console or Console()
        self.show_risk_level = show_risk_level
        self.show_preview = show_preview
        self.always_approve: set[str] = set()  # Tools to auto-approve
        self.never_approve: set[str] = set()  # Tools to auto-deny

    def _display_tool_call(self, request: ToolApprovalRequest) -> None:
        """Display tool call information in a Rich panel (blocking I/O).

        Args:
            request: Approval request with tool info
        """
        # Build panel content
        lines = []

        # Tool name and description
        lines.append(f"[bold cyan]Tool:[/bold cyan] {request.tool_name}")
        if request.description:
            lines.append(f"[dim]{request.description}[/dim]")

        # Risk level
        if self.show_risk_level:
            risk_color = {
                "safe": "green",
                "caution": "yellow",
                "dangerous": "red",
                "blocked": "red bold",
            }.get(request.risk_level.value, "white")
            lines.append(
                f"\n[bold]Risk Level:[/bold] [{risk_color}]{request.risk_level.value.upper()}[/{risk_color}]"
            )

        # Arguments (formatted JSON)
        if request.arguments:
            lines.append("\n[bold]Arguments:[/bold]")
            args_json = json.dumps(request.arguments, indent=2)
            # Use Syntax for JSON highlighting
            syntax = Syntax(args_json, "json", theme="monokai", line_numbers=False)
            self.console.print()  # Spacing before syntax
            self.console.print(
                Panel("\n".join(lines), title="Tool Call", border_style="cyan")
            )
            self.console.print(syntax)
            return

        # Show panel without arguments
        self.console.print(
            Panel("\n".join(lines), title="Tool Call", border_style="cyan")
        )

        # Show diff preview for file operations
        if self.show_preview and request.preview:
            preview_syntax = Syntax(
                request.preview, "diff", theme="monokai", line_numbers=True
            )
            self.console.print("\n[bold]Preview:[/bold]")
            self.console.print(preview_syntax)

    def _get_user_choice(self) -> str:
        """Get user approval choice (blocking I/O).

        Returns:
            User's choice: 'y', 'n', 'a', or 'v'
        """
        return Prompt.ask(
            "\nApprove execution?",
            choices=["y", "n", "a", "v"],
            default="y",
            show_choices=True,
            console=self.console,
        )

    async def request_approval(
        self,
        request: ToolApprovalRequest,
    ) -> ToolApprovalResponse:
        """Show CLI prompt and get user approval (non-blocking).

        Displays tool information in a Rich panel and prompts for approval
        with y/n/a/v options:
        - y: Yes, approve this execution
        - n: No, deny this execution
        - a: Always approve this tool (session-level)
        - v: neVer approve this tool (session-level)

        Uses asyncio.to_thread to avoid blocking the event loop during I/O.

        Args:
            request: Approval request with tool info

        Returns:
            ToolApprovalResponse with user's decision and metadata
        """
        # Display tool call info in thread to avoid blocking event loop
        await asyncio.to_thread(self._display_tool_call, request)

        # Get user choice in thread to avoid blocking event loop
        choice = await asyncio.to_thread(self._get_user_choice)

        # Process choice
        if choice == "y":
            self.console.print("[green]✓ Approved[/green]")
            return ToolApprovalResponse(approved=True)

        elif choice == "n":
            self.console.print("[red]✗ Denied[/red]")
            return ToolApprovalResponse(
                approved=False, reason="User denied via CLI prompt"
            )

        elif choice == "a":
            # Always approve this tool for the session
            self.always_approve.add(request.tool_name)
            self.console.print(
                f"[green]✓ Approved (always approve '{request.tool_name}' for this session)[/green]"
            )
            return ToolApprovalResponse(
                approved=True,
                metadata={"always_approve": True},
            )

        elif choice == "v":
            # Never approve this tool for the session
            self.never_approve.add(request.tool_name)
            self.console.print(
                f"[red]✗ Denied (never approve '{request.tool_name}' for this session)[/red]"
            )
            return ToolApprovalResponse(
                approved=False,
                reason="User selected 'never approve' for this tool",
                metadata={"never_approve": True},
            )

        else:
            # Should never reach here due to Prompt.ask validation
            return ToolApprovalResponse(approved=False, reason="Invalid choice")

    def clear_session_state(self) -> None:
        """Clear session-level approval tracking.

        Resets always_approve and never_approve sets. Useful when starting
        a new conversation or resetting session state.
        """
        self.always_approve.clear()
        self.never_approve.clear()
