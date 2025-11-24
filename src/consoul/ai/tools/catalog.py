"""Tool catalog for SDK tool specification.

Provides mappings between friendly tool names and actual tool instances,
enabling flexible tool specification in the SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from consoul.ai.tools.base import RiskLevel
from consoul.ai.tools.implementations.bash import bash_execute
from consoul.ai.tools.implementations.code_search import code_search
from consoul.ai.tools.implementations.file_edit import (
    append_to_file,
    create_file,
    delete_file,
    edit_file_lines,
    edit_file_search_replace,
)
from consoul.ai.tools.implementations.find_references import find_references
from consoul.ai.tools.implementations.grep_search import grep_search

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


# Tool catalog: Maps friendly names to (tool_instance, risk_level) tuples
TOOL_CATALOG: dict[str, tuple[BaseTool, RiskLevel]] = {
    "bash": (bash_execute, RiskLevel.CAUTION),
    "grep": (grep_search, RiskLevel.SAFE),
    "code_search": (code_search, RiskLevel.SAFE),
    "find_references": (find_references, RiskLevel.SAFE),
    "create_file": (create_file, RiskLevel.CAUTION),
    "edit_lines": (edit_file_lines, RiskLevel.CAUTION),
    "edit_replace": (edit_file_search_replace, RiskLevel.CAUTION),
    "append_file": (append_to_file, RiskLevel.CAUTION),
    "delete_file": (delete_file, RiskLevel.DANGEROUS),
}

# Alias mappings for convenience
TOOL_ALIASES: dict[str, str] = {
    "bash_execute": "bash",
    "grep_search": "grep",
    "find_refs": "find_references",
    "edit_file_lines": "edit_lines",
    "edit_file_search_replace": "edit_replace",
}


def get_tool_by_name(name: str) -> tuple[BaseTool, RiskLevel] | None:
    """Get tool and risk level by friendly name.

    Args:
        name: Tool name (e.g., "bash", "grep")

    Returns:
        Tuple of (tool, risk_level) if found, None otherwise

    Example:
        >>> tool, risk = get_tool_by_name("bash")
        >>> assert risk == RiskLevel.CAUTION
    """
    # Check direct name
    if name in TOOL_CATALOG:
        return TOOL_CATALOG[name]

    # Check aliases
    if name in TOOL_ALIASES:
        canonical_name = TOOL_ALIASES[name]
        return TOOL_CATALOG[canonical_name]

    return None


def get_tools_by_risk_level(risk: str | RiskLevel) -> list[tuple[BaseTool, RiskLevel]]:
    """Get all tools matching or below the specified risk level.

    Args:
        risk: Risk level filter ("safe", "caution", "dangerous")

    Returns:
        List of (tool, risk_level) tuples

    Example:
        >>> tools = get_tools_by_risk_level("safe")
        >>> assert all(risk == RiskLevel.SAFE for _, risk in tools)
    """
    if isinstance(risk, str):
        risk = RiskLevel(risk.lower())

    # Define risk hierarchy
    risk_hierarchy = {
        RiskLevel.SAFE: [RiskLevel.SAFE],
        RiskLevel.CAUTION: [RiskLevel.SAFE, RiskLevel.CAUTION],
        RiskLevel.DANGEROUS: [RiskLevel.SAFE, RiskLevel.CAUTION, RiskLevel.DANGEROUS],
    }

    allowed_levels = risk_hierarchy.get(risk, [])
    return [
        (tool, tool_risk)
        for tool, tool_risk in TOOL_CATALOG.values()
        if tool_risk in allowed_levels
    ]


def get_all_tool_names() -> list[str]:
    """Get list of all available tool names.

    Returns:
        Sorted list of tool names

    Example:
        >>> names = get_all_tool_names()
        >>> assert "bash" in names
        >>> assert "grep" in names
    """
    return sorted(TOOL_CATALOG.keys())


def validate_tool_name(name: str) -> bool:
    """Check if a tool name is valid.

    Args:
        name: Tool name to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> assert validate_tool_name("bash") is True
        >>> assert validate_tool_name("invalid") is False
    """
    return name in TOOL_CATALOG or name in TOOL_ALIASES
