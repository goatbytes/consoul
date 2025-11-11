"""TUI approval provider implementation.

Provides Textual-based approval UI that implements the ApprovalProvider protocol
from the core approval API (SOUL-66).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from consoul.ai.tools.approval import (
    ToolApprovalRequest,
    ToolApprovalResponse,
)

if TYPE_CHECKING:
    from consoul.tui.app import ConsoulApp


class TuiApprovalProvider:
    """TUI-based approval provider using Textual modal.

    Implements the ApprovalProvider protocol by showing a rich modal dialog
    with tool information, risk indicators, and approve/deny buttons.

    Example:
        >>> from consoul.tui.app import ConsoulApp
        >>> from consoul.tui.tools import TuiApprovalProvider
        >>> from consoul.ai.tools import ToolRegistry
        >>> from consoul.config.models import ToolConfig
        >>>
        >>> app = ConsoulApp()
        >>> provider = TuiApprovalProvider(app)
        >>> config = ToolConfig(enabled=True)
        >>> registry = ToolRegistry(config, approval_provider=provider)
        >>> # Tool execution will now show TUI approval modal
    """

    def __init__(self, app: ConsoulApp) -> None:
        """Initialize TUI approval provider.

        Args:
            app: ConsoulApp instance for showing modals
        """
        self.app = app

    async def request_approval(
        self,
        request: ToolApprovalRequest,
    ) -> ToolApprovalResponse:
        """Request approval via TUI modal dialog.

        Shows a Textual modal with tool information, risk level, and
        approve/deny buttons. Waits for user decision.

        Args:
            request: Approval request with tool information

        Returns:
            ToolApprovalResponse with user's decision

        Example:
            >>> from consoul.ai.tools import RiskLevel
            >>> request = ToolApprovalRequest(
            ...     tool_name="bash_execute",
            ...     arguments={"command": "ls -la"},
            ...     risk_level=RiskLevel.SAFE,
            ...     tool_call_id="call_123"
            ... )
            >>> response = await provider.request_approval(request)
            >>> if response.approved:
            ...     # Execute tool
            ...     pass
        """
        # Import here to avoid circular dependency
        from consoul.tui.widgets.tool_approval_modal import ToolApprovalModal

        # Show modal and wait for result
        approved = await self.app.push_screen_wait(ToolApprovalModal(request))

        return ToolApprovalResponse(
            approved=approved,
            reason=None if approved else "User denied via TUI modal",
        )
