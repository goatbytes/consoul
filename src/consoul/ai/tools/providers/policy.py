"""Policy-based approval provider for backend/headless environments.

Provides automatic approval based on configurable policies:
- Tool whitelist: Always approve specific tools by name
- Risk threshold: Auto-approve tools up to a certain risk level
- Auto-approve all: Approve everything (DANGEROUS - use with caution)

This provider NEVER blocks on stdin/terminal input, making it suitable
for production backend services, web applications, and headless deployments.

Example:
    >>> from consoul.ai.tools.providers import PolicyBasedApprovalProvider
    >>> from consoul.ai.tools.base import RiskLevel
    >>>
    >>> # Auto-approve SAFE and CAUTION tools
    >>> provider = PolicyBasedApprovalProvider(max_risk=RiskLevel.CAUTION)
    >>>
    >>> # Whitelist specific tools
    >>> provider = PolicyBasedApprovalProvider(
    ...     whitelist={"bash_execute", "grep_search"},
    ...     max_risk=RiskLevel.SAFE
    ... )
    >>>
    >>> # Use in service factory
    >>> from consoul.sdk.services import ToolService
    >>> service = ToolService.from_config(config, approval_provider=provider)
"""

from __future__ import annotations

import logging

from consoul.ai.tools.approval import (
    ToolApprovalRequest,
    ToolApprovalResponse,
)
from consoul.ai.tools.base import RiskLevel

logger = logging.getLogger(__name__)

# Priority map for safe risk level comparison
# Lower number = safer; higher number = more dangerous
# DO NOT compare RiskLevel.value strings directly - they are not ordered!
RISK_PRIORITY: dict[RiskLevel, int] = {
    RiskLevel.SAFE: 0,
    RiskLevel.CAUTION: 1,
    RiskLevel.DANGEROUS: 2,
    RiskLevel.BLOCKED: 3,
}


class PolicyBasedApprovalProvider:
    """Non-blocking approval provider for production backend use.

    Auto-approves tool execution based on configurable policies.
    Never prompts for user input, making it safe for headless environments.

    Approval Rules (evaluated in order):
    1. If auto_approve_all=True: approve everything
    2. If tool_name in whitelist: approve
    3. If tool's risk level <= max_risk: approve
    4. Otherwise: deny

    Attributes:
        whitelist: Set of tool names to always approve
        max_risk: Maximum risk level to auto-approve (default: SAFE)
        auto_approve_all: Approve everything (DANGEROUS - document why you need this)

    Example - Approve safe tools + specific caution tools:
        >>> provider = PolicyBasedApprovalProvider(
        ...     whitelist={"file_edit", "bash_execute"},
        ...     max_risk=RiskLevel.SAFE  # Only whitelist bypasses this
        ... )

    Example - Approve all tools up to CAUTION level:
        >>> provider = PolicyBasedApprovalProvider(
        ...     max_risk=RiskLevel.CAUTION  # SAFE and CAUTION approved
        ... )

    Example - Approve everything (DANGEROUS):
        >>> # Only use for testing or fully trusted environments!
        >>> provider = PolicyBasedApprovalProvider(auto_approve_all=True)

    Security Notes:
        - Never use auto_approve_all in multi-tenant environments
        - Whitelist should be as restrictive as possible
        - max_risk=DANGEROUS is extremely permissive, use with caution
        - BLOCKED tools are never approved even with auto_approve_all=True
    """

    def __init__(
        self,
        whitelist: set[str] | None = None,
        max_risk: RiskLevel = RiskLevel.SAFE,
        auto_approve_all: bool = False,
    ) -> None:
        """Initialize policy-based approval provider.

        Args:
            whitelist: Set of tool names to always approve (bypasses risk check)
            max_risk: Maximum risk level to auto-approve. Tools with risk
                level <= max_risk are approved. Default is SAFE (most restrictive).
            auto_approve_all: Approve ALL tool requests (DANGEROUS - for testing
                or fully trusted environments only). BLOCKED tools are still denied.

        Raises:
            ValueError: If max_risk is BLOCKED (nothing should be auto-approved at BLOCKED)
        """
        if max_risk == RiskLevel.BLOCKED:
            raise ValueError(
                "max_risk cannot be BLOCKED. Use auto_approve_all=True if you "
                "need to approve DANGEROUS tools, but BLOCKED should never be approved."
            )

        self.whitelist = whitelist or set()
        self.max_risk = max_risk
        self.auto_approve_all = auto_approve_all

        if auto_approve_all:
            logger.warning(
                "PolicyBasedApprovalProvider created with auto_approve_all=True. "
                "All tool executions will be approved without user interaction. "
                "This is DANGEROUS in production environments."
            )

    async def request_approval(
        self,
        request: ToolApprovalRequest,
    ) -> ToolApprovalResponse:
        """Evaluate policy and return approval decision immediately.

        This method NEVER blocks on user input. Decisions are made based
        on the configured policy (whitelist, risk threshold, auto-approve).

        Args:
            request: Approval request with tool information

        Returns:
            ToolApprovalResponse with policy-based decision

        Note:
            BLOCKED tools are ALWAYS denied, even with auto_approve_all=True.
            This is a safety guardrail against catastrophic operations.
        """
        tool_name = request.tool_name
        risk_level = request.risk_level

        # BLOCKED tools are NEVER approved (safety guardrail)
        if risk_level == RiskLevel.BLOCKED:
            logger.warning(
                f"Tool '{tool_name}' denied: BLOCKED tools are never approved"
            )
            return ToolApprovalResponse(
                approved=False,
                reason=f"Tool '{tool_name}' is BLOCKED and cannot be executed",
                metadata={"policy": "blocked_guardrail"},
            )

        # Rule 1: Auto-approve all (if enabled)
        if self.auto_approve_all:
            logger.debug(f"Tool '{tool_name}' approved: auto_approve_all=True")
            return ToolApprovalResponse(
                approved=True,
                metadata={"policy": "auto_approve_all"},
            )

        # Rule 2: Whitelist approval
        if tool_name in self.whitelist:
            logger.debug(f"Tool '{tool_name}' approved: in whitelist")
            return ToolApprovalResponse(
                approved=True,
                metadata={"policy": "whitelist"},
            )

        # Rule 3: Risk threshold approval
        # Use priority map for safe comparison (SAFE=0 < CAUTION=1 < DANGEROUS=2)
        request_priority = RISK_PRIORITY.get(risk_level, 999)
        max_priority = RISK_PRIORITY.get(self.max_risk, 0)

        if request_priority <= max_priority:
            logger.debug(
                f"Tool '{tool_name}' approved: risk={risk_level.value} "
                f"<= max_risk={self.max_risk.value}"
            )
            return ToolApprovalResponse(
                approved=True,
                metadata={
                    "policy": "risk_threshold",
                    "tool_risk": risk_level.value,
                    "max_risk": self.max_risk.value,
                },
            )

        # Deny: exceeds risk threshold and not whitelisted
        reason = (
            f"Tool '{tool_name}' (risk={risk_level.value}) "
            f"exceeds max_risk={self.max_risk.value} and is not in whitelist"
        )
        logger.debug(f"Tool '{tool_name}' denied: {reason}")
        return ToolApprovalResponse(
            approved=False,
            reason=reason,
            metadata={
                "policy": "risk_exceeded",
                "tool_risk": risk_level.value,
                "max_risk": self.max_risk.value,
            },
        )
