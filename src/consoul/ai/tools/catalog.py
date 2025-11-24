"""Tool catalog for SDK tool specification.

Provides mappings between friendly tool names and actual tool instances,
enabling flexible tool specification in the SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from consoul.ai.tools.base import RiskLevel, ToolCategory
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
from consoul.ai.tools.implementations.read_url import read_url
from consoul.ai.tools.implementations.web_search import web_search

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


# Tool catalog: Maps friendly names to (tool_instance, risk_level, categories) tuples
TOOL_CATALOG: dict[str, tuple[BaseTool, RiskLevel, list[ToolCategory]]] = {
    "bash": (bash_execute, RiskLevel.CAUTION, [ToolCategory.EXECUTE]),
    "grep": (grep_search, RiskLevel.SAFE, [ToolCategory.SEARCH]),
    "code_search": (code_search, RiskLevel.SAFE, [ToolCategory.SEARCH]),
    "find_references": (find_references, RiskLevel.SAFE, [ToolCategory.SEARCH]),
    "create_file": (create_file, RiskLevel.CAUTION, [ToolCategory.FILE_EDIT]),
    "edit_lines": (edit_file_lines, RiskLevel.CAUTION, [ToolCategory.FILE_EDIT]),
    "edit_replace": (
        edit_file_search_replace,
        RiskLevel.CAUTION,
        [ToolCategory.FILE_EDIT],
    ),
    "append_file": (append_to_file, RiskLevel.CAUTION, [ToolCategory.FILE_EDIT]),
    "delete_file": (delete_file, RiskLevel.DANGEROUS, [ToolCategory.FILE_EDIT]),
    "read_url": (read_url, RiskLevel.SAFE, [ToolCategory.WEB]),
    "web_search": (web_search, RiskLevel.SAFE, [ToolCategory.WEB]),
}

# Alias mappings for convenience
TOOL_ALIASES: dict[str, str] = {
    "bash_execute": "bash",
    "grep_search": "grep",
    "find_refs": "find_references",
    "edit_file_lines": "edit_lines",
    "edit_file_search_replace": "edit_replace",
}


def get_tool_by_name(
    name: str,
) -> tuple[BaseTool, RiskLevel, list[ToolCategory]] | None:
    """Get tool, risk level, and categories by friendly name.

    Args:
        name: Tool name (e.g., "bash", "grep")

    Returns:
        Tuple of (tool, risk_level, categories) if found, None otherwise

    Example:
        >>> result = get_tool_by_name("bash")
        >>> if result:
        ...     tool, risk, categories = result
        ...     assert risk == RiskLevel.CAUTION
    """
    # Check direct name
    if name in TOOL_CATALOG:
        return TOOL_CATALOG[name]

    # Check aliases
    if name in TOOL_ALIASES:
        canonical_name = TOOL_ALIASES[name]
        return TOOL_CATALOG[canonical_name]

    return None


def get_tools_by_risk_level(
    risk: str | RiskLevel,
) -> list[tuple[BaseTool, RiskLevel, list[ToolCategory]]]:
    """Get all tools matching or below the specified risk level.

    Args:
        risk: Risk level filter ("safe", "caution", "dangerous")

    Returns:
        List of (tool, risk_level, categories) tuples

    Example:
        >>> tools = get_tools_by_risk_level("safe")
        >>> assert all(risk == RiskLevel.SAFE for _, risk, _ in tools)
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
        (tool, tool_risk, categories)
        for tool, tool_risk, categories in TOOL_CATALOG.values()
        if tool_risk in allowed_levels
    ]


def get_tools_by_category(
    category: str | ToolCategory,
) -> list[tuple[BaseTool, RiskLevel, list[ToolCategory]]]:
    """Get all tools in a specific category.

    Args:
        category: Category filter (e.g., "search", "file-edit", "web")

    Returns:
        List of (tool, risk_level, categories) tuples

    Example:
        >>> tools = get_tools_by_category("search")
        >>> assert len(tools) > 0
        >>> for tool, _, cats in tools:
        ...     assert ToolCategory.SEARCH in cats
    """
    if isinstance(category, str):
        category = ToolCategory(category.lower())

    return [
        (tool, risk_level, categories)
        for tool, risk_level, categories in TOOL_CATALOG.values()
        if category in categories
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


def get_all_category_names() -> list[str]:
    """Get list of all available category names.

    Returns:
        Sorted list of category names

    Example:
        >>> names = get_all_category_names()
        >>> assert "search" in names
        >>> assert "file-edit" in names
    """
    return sorted([category.value for category in ToolCategory])


def validate_category_name(name: str) -> bool:
    """Check if a category name is valid.

    Args:
        name: Category name to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> assert validate_category_name("search") is True
        >>> assert validate_category_name("invalid") is False
    """
    try:
        ToolCategory(name.lower())
        return True
    except ValueError:
        return False
