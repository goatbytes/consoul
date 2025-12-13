"""Top bar state builder utility.

Calculates top bar UI state from app state components.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.ai.tools import ToolRegistry
    from consoul.config import ConsoulConfig

import logging

logger = logging.getLogger(__name__)


def build_top_bar_state(
    consoul_config: ConsoulConfig | None,
    current_profile: str,
    current_model: str,
    streaming: bool,
    tool_registry: ToolRegistry | None,
    conversation_count: int | None = None,
) -> dict[str, Any]:
    """Build top bar state dictionary from app components.

    Args:
        consoul_config: Consoul configuration (may be None)
        current_profile: Current profile name
        current_model: Current model name
        streaming: Whether currently streaming
        tool_registry: Tool registry (may be None)
        conversation_count: Number of conversations (may be None)

    Returns:
        Dictionary with keys: current_provider, current_model, current_profile,
        streaming, conversation_count, tools_enabled, highest_risk
    """
    state: dict[str, Any] = {}

    # Update provider and model (from config, not profile)
    if consoul_config:
        state["current_provider"] = consoul_config.current_provider.value
        state["current_model"] = consoul_config.current_model
    else:
        state["current_provider"] = ""
        state["current_model"] = current_model

    # Update profile name
    state["current_profile"] = current_profile

    # Update streaming status
    state["streaming"] = streaming

    # Update conversation count
    state["conversation_count"] = conversation_count or 0

    # Update tool status
    if tool_registry:
        # Get enabled tools
        enabled_tools = tool_registry.list_tools(enabled_only=True)
        state["tools_enabled"] = len(enabled_tools)

        # Determine highest risk level
        if not enabled_tools:
            state["highest_risk"] = "none"
        else:
            from consoul.ai.tools.base import RiskLevel

            # Find highest risk among enabled tools
            risk_hierarchy = {
                RiskLevel.SAFE: 0,
                RiskLevel.CAUTION: 1,
                RiskLevel.DANGEROUS: 2,
            }

            max_risk = max(
                risk_hierarchy.get(meta.risk_level, 0) for meta in enabled_tools
            )

            # Map back to string
            if max_risk == 2:
                state["highest_risk"] = "dangerous"
            elif max_risk == 1:
                state["highest_risk"] = "caution"
            else:
                state["highest_risk"] = "safe"
    else:
        # No registry (shouldn't happen, but defensive)
        state["tools_enabled"] = 0
        state["highest_risk"] = "none"

    return state
