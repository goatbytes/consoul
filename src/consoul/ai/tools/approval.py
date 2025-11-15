"""Headless approval API for tool execution.

Provides Protocol-based approval system that works without TUI dependencies,
enabling SDK consumers to implement custom approval workflows (CLI prompts,
web UI, IDE dialogs, etc.).

This module is the foundation for SOUL-59 (TUI modal) and SOUL-62 (execution flow).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from consoul.ai.tools.base import RiskLevel


@dataclass
class ToolApprovalRequest:
    """Request for tool execution approval.

    Contains all information needed for approval provider to make
    an informed decision and show appropriate UI.

    Attributes:
        tool_name: Name of the tool requesting execution
        arguments: Tool arguments (e.g., {"command": "ls -la"})
        risk_level: Security risk assessment (SAFE, CAUTION, DANGEROUS)
        tool_call_id: Unique identifier for this tool call from AI message
        description: Human-readable tool description
        preview: Optional diff preview for file operations (unified diff format)
        context: Additional metadata for host app (user_id, session_id, etc.)

    Example:
        >>> from consoul.ai.tools import RiskLevel
        >>> request = ToolApprovalRequest(
        ...     tool_name="bash_execute",
        ...     arguments={"command": "ls -la"},
        ...     risk_level=RiskLevel.SAFE,
        ...     tool_call_id="call_abc123",
        ...     description="Execute bash command",
        ...     context={"user": "jared@goatbytes.io"}
        ... )
    """

    tool_name: str
    arguments: dict[str, Any]
    risk_level: RiskLevel
    tool_call_id: str
    description: str = ""
    preview: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolApprovalResponse:
    """Response from approval provider with decision.

    Attributes:
        approved: Whether tool execution was approved
        reason: Optional reason for denial (shown to user/logged)
        timeout_override: Override default timeout in seconds (None = use default)
        metadata: Additional response metadata (e.g., approval timestamp)

    Example:
        >>> # Approval
        >>> response = ToolApprovalResponse(approved=True)
        >>>
        >>> # Denial with reason
        >>> response = ToolApprovalResponse(
        ...     approved=False,
        ...     reason="User denied: command too dangerous"
        ... )
        >>>
        >>> # Approval with custom timeout
        >>> response = ToolApprovalResponse(
        ...     approved=True,
        ...     timeout_override=60  # 60 seconds instead of default
        ... )
    """

    approved: bool
    reason: str | None = None
    timeout_override: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ApprovalProvider(Protocol):
    """Protocol for tool execution approval providers.

    Approval providers implement the approval UX (CLI prompts, web UI,
    TUI modals, IDE dialogs, etc.) and return the user's decision.

    The registry will call request_approval() and wait for the response
    before executing tools.

    Implementation Examples:

    CLI Approval:
        >>> class CliApprovalProvider:
        ...     async def request_approval(
        ...         self, request: ToolApprovalRequest
        ...     ) -> ToolApprovalResponse:
        ...         print(f"Tool: {request.tool_name}")
        ...         print(f"Args: {request.arguments}")
        ...         print(f"Risk: {request.risk_level.value.upper()}")
        ...         response = input("Approve? (y/n): ")
        ...         return ToolApprovalResponse(
        ...             approved=response.lower() == 'y',
        ...             reason=None if response.lower() == 'y' else "User denied"
        ...         )

    Auto-Approve (DANGEROUS - testing only):
        >>> class AutoApproveProvider:
        ...     async def request_approval(
        ...         self, request: ToolApprovalRequest
        ...     ) -> ToolApprovalResponse:
        ...         return ToolApprovalResponse(approved=True)

    TUI Modal (implemented in SOUL-59):
        >>> class TuiApprovalProvider:
        ...     def __init__(self, app):
        ...         self.app = app
        ...
        ...     async def request_approval(
        ...         self, request: ToolApprovalRequest
        ...     ) -> ToolApprovalResponse:
        ...         from consoul.tui.widgets import ToolApprovalModal
        ...         modal = ToolApprovalModal(request)
        ...         approved = await self.app.push_screen_wait(modal)
        ...         return ToolApprovalResponse(
        ...             approved=approved,
        ...             reason=None if approved else "User denied via TUI"
        ...         )
    """

    async def request_approval(
        self,
        request: ToolApprovalRequest,
    ) -> ToolApprovalResponse:
        """Request approval for tool execution.

        This method is called by the tool registry when a tool needs
        approval. Implementation should show appropriate UI and return
        the user's decision.

        Args:
            request: Approval request with tool information

        Returns:
            ToolApprovalResponse with approval decision

        Raises:
            Any exceptions should be handled by the implementation.
            Raising an exception will be treated as denial.
        """
        ...


class ApprovalError(Exception):
    """Raised when approval process fails.

    Distinct from approval denial (which is normal workflow).
    This indicates an error in the approval provider itself.

    Example:
        >>> raise ApprovalError("Failed to connect to approval service")
    """
