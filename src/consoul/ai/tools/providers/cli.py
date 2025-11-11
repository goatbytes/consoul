"""CLI-based approval provider for terminal environments."""

from __future__ import annotations

from consoul.ai.tools.approval import (
    ToolApprovalRequest,
    ToolApprovalResponse,
)


class CliApprovalProvider:
    """Command-line approval provider using input().

    Displays tool information in terminal and prompts user for approval.
    Suitable for CLI applications, testing, and headless environments with
    terminal access.

    Example:
        >>> from consoul.ai.tools import ToolRegistry
        >>> from consoul.ai.tools.providers import CliApprovalProvider
        >>> from consoul.config.models import ToolConfig
        >>>
        >>> provider = CliApprovalProvider()
        >>> config = ToolConfig(enabled=True)
        >>> registry = ToolRegistry(config, approval_provider=provider)
        >>> # Now registry will use CLI prompts for approval
    """

    def __init__(self, *, show_arguments: bool = True, verbose: bool = False):
        """Initialize CLI approval provider.

        Args:
            show_arguments: Whether to display tool arguments in prompt
            verbose: Show additional details (risk level, context, description)
        """
        self.show_arguments = show_arguments
        self.verbose = verbose

    async def request_approval(
        self,
        request: ToolApprovalRequest,
    ) -> ToolApprovalResponse:
        """Show CLI prompt and get user approval.

        Displays tool information in a formatted box and prompts for y/n response.

        Args:
            request: Approval request with tool info

        Returns:
            ToolApprovalResponse with user's decision
        """
        # Display tool information
        print(f"\n{'=' * 60}")
        print(f"Tool Execution Request: {request.tool_name}")
        print(f"{'=' * 60}")

        if self.verbose and request.description:
            print(f"Description: {request.description}")

        if self.show_arguments and request.arguments:
            print("\nArguments:")
            for key, value in request.arguments.items():
                # Format value (truncate if too long)
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                print(f"  {key}: {value_str}")

        if self.verbose:
            print(f"\nRisk Level: {request.risk_level.value.upper()}")
            if request.context:
                print(f"Context: {request.context}")

        # Get user decision
        print(f"\n{'=' * 60}")
        while True:
            response = input("Approve execution? (y/n): ").strip().lower()
            if response in ("y", "yes"):
                print("✓ Approved")
                return ToolApprovalResponse(approved=True)
            elif response in ("n", "no"):
                print("✗ Denied")
                return ToolApprovalResponse(
                    approved=False, reason="User denied via CLI prompt"
                )
            else:
                print("Please enter 'y' or 'n'")
