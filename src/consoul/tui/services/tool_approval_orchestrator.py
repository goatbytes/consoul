"""Tool Approval Orchestration Service.

Handles the business logic for tool approval workflow including risk assessment,
auto-approval checks, audit logging, and approval request construction.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.ai.tools import ToolApprovalRequest
    from consoul.ai.tools.audit import AuditLogger
    from consoul.ai.tools.base import RiskLevel
    from consoul.ai.tools.parser import ParsedToolCall
    from consoul.ai.tools.permissions.analyzer import CommandRisk
    from consoul.ai.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

__all__ = ["ToolApprovalOrchestrator"]


class ToolApprovalOrchestrator:
    """Orchestrates tool approval workflow.

    Separates approval business logic from TUI event handlers, making the
    approval flow reusable across different interfaces (TUI, CLI, API).

    Args:
        tool_registry: Tool registry for risk assessment and policy checks
        audit_logger: Optional audit logger for tracking approval events
    """

    def __init__(
        self,
        tool_registry: ToolRegistry | None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        """Initialize orchestrator with registry and audit logger."""
        self.tool_registry = tool_registry
        self.audit_logger = audit_logger
        self._approval_start_times: dict[str, float] = {}

    async def assess_tool_call(self, tool_call: ParsedToolCall) -> CommandRisk:
        """Assess risk for tool call.

        Args:
            tool_call: Tool call to assess

        Returns:
            CommandRisk assessment
        """
        from consoul.ai.tools import RiskLevel
        from consoul.ai.tools.permissions.analyzer import CommandRisk

        if self.tool_registry is None:
            logger.warning("No tool registry available for risk assessment")
            return CommandRisk(
                level=RiskLevel.DANGEROUS,
                reason="No tool registry available",
            )

        try:
            risk_assessment: CommandRisk = self.tool_registry.assess_risk(
                tool_call.name,
                tool_call.arguments,
            )
            return risk_assessment
        except Exception as e:
            logger.error(
                f"Failed to assess risk for tool '{tool_call.name}': {e}",
                exc_info=True,
            )
            return CommandRisk(
                level=RiskLevel.DANGEROUS,
                reason=f"Tool not found or assessment failed: {e}",
            )

    async def check_auto_approval(
        self, tool_call: ParsedToolCall, risk_level: RiskLevel
    ) -> tuple[bool, str | None]:
        """Check if tool should be auto-approved based on policy.

        Auto-approval happens when:
        - BALANCED policy auto-approves SAFE commands
        - TRUSTING policy auto-approves SAFE+CAUTION commands
        - Command is whitelisted

        Args:
            tool_call: Tool call to check
            risk_level: Assessed risk level

        Returns:
            Tuple of (should_auto_approve, reason)
        """
        if self.tool_registry is None:
            return (False, None)

        try:
            needs_approval = self.tool_registry.needs_approval(
                tool_call.name, tool_call.arguments
            )
            logger.debug(
                f"[TOOL_FLOW] Approval check for {tool_call.name}: "
                f"needs_approval={needs_approval}"
            )

            if not needs_approval:
                reason = f"Auto-approved by policy ({risk_level.value})"
                return (True, reason)

            return (False, None)
        except Exception as e:
            logger.error(
                f"Error checking approval for '{tool_call.name}': {e}",
                exc_info=True,
            )
            return (False, None)

    async def log_request(self, tool_call: ParsedToolCall) -> float:
        """Log tool approval request event.

        Args:
            tool_call: Tool call being requested

        Returns:
            Start time for duration tracking
        """
        from consoul.ai.tools.audit import AuditEvent

        start_time = time.time()
        self._approval_start_times[tool_call.id] = start_time

        if self.audit_logger:
            await self.audit_logger.log_event(
                AuditEvent(
                    event_type="request",
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                )
            )

        return start_time

    async def log_decision(
        self,
        tool_call: ParsedToolCall,
        approved: bool,
        reason: str | None = None,
    ) -> None:
        """Log approval decision event.

        Args:
            tool_call: Tool call that was approved/denied
            approved: Whether approval was granted
            reason: Optional reason for decision
        """
        from typing import Literal

        from consoul.ai.tools.audit import AuditEvent

        if not self.audit_logger:
            return

        # Calculate duration
        start_time = self._approval_start_times.get(tool_call.id, time.time())
        duration_ms = int((time.time() - start_time) * 1000)

        # Clean up start time
        self._approval_start_times.pop(tool_call.id, None)

        event_type: Literal["approval", "denial"] = "approval" if approved else "denial"
        result = reason if not approved else None

        await self.audit_logger.log_event(
            AuditEvent(
                event_type=event_type,
                tool_name=tool_call.name,
                arguments=tool_call.arguments,
                decision=approved,
                result=result,
                duration_ms=duration_ms,
            )
        )

    def build_approval_request(
        self, tool_call: ParsedToolCall, risk_assessment: CommandRisk
    ) -> ToolApprovalRequest:
        """Build ToolApprovalRequest from tool call and risk assessment.

        Args:
            tool_call: Tool call needing approval
            risk_assessment: Risk assessment result

        Returns:
            ToolApprovalRequest ready for approval provider
        """
        from consoul.ai.tools import ToolApprovalRequest

        return ToolApprovalRequest(
            tool_name=tool_call.name,
            arguments=tool_call.arguments,
            risk_level=risk_assessment.level,
            tool_call_id=tool_call.id,
            description=risk_assessment.reason,
        )

    def should_reject_immediately(
        self, risk_assessment: CommandRisk
    ) -> tuple[bool, str | None]:
        """Check if tool should be rejected immediately without modal.

        This happens when tool doesn't exist in registry.

        Args:
            risk_assessment: Risk assessment result

        Returns:
            Tuple of (should_reject, error_message)
        """
        from consoul.ai.tools import RiskLevel

        # If tool not found, immediately reject with helpful error
        if (
            risk_assessment.level == RiskLevel.DANGEROUS
            and "Tool not found" in risk_assessment.reason
            and self.tool_registry
        ):
            # Get available tools for error message
            tool_names = [t.name for t in self.tool_registry.list_tools()]
            available_tools = ", ".join(tool_names)
            # Extract tool name from error message
            parts = risk_assessment.reason.split("'")
            tool_name = parts[1] if len(parts) > 1 else "unknown"
            error_msg = (
                f"Tool '{tool_name}' does not exist. Available tools: {available_tools}"
            )
            return (True, error_msg)

        return (False, None)
