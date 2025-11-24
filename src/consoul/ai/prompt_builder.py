"""Dynamic system prompt building for Consoul.

This module provides utilities for building system prompts dynamically based on
the current tool registry state, eliminating hardcoded tool lists and reducing
token waste when tools are disabled.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.ai.tools.base import ToolMetadata
    from consoul.ai.tools.registry import ToolRegistry


def build_system_prompt(
    base_prompt: str | None,
    tool_registry: ToolRegistry | None,
) -> str | None:
    """Build system prompt with dynamic tool documentation.

    Replaces the {AVAILABLE_TOOLS} marker in the base prompt with a dynamically
    generated tools section based on currently enabled tools.

    Args:
        base_prompt: Base system prompt template (may contain {AVAILABLE_TOOLS})
        tool_registry: Tool registry to query for enabled tools (optional)

    Returns:
        Complete system prompt with tool documentation, or None if no base prompt

    Example:
        >>> prompt = build_system_prompt(
        ...     "You are an AI assistant.\\n\\n{AVAILABLE_TOOLS}",
        ...     tool_registry
        ... )
        >>> "bash_execute" in prompt
        True
    """
    if not base_prompt:
        return None

    # If no marker present, return as-is (backward compatibility)
    if "{AVAILABLE_TOOLS}" not in base_prompt:
        return base_prompt

    # Build tools section
    if not tool_registry:
        tools_section = _format_no_tools_message()
    else:
        enabled_tools = tool_registry.list_tools(enabled_only=True)
        if not enabled_tools:
            tools_section = _format_no_tools_message()
        else:
            tools_section = format_tools_documentation(enabled_tools)

    # Replace marker with generated content
    return base_prompt.replace("{AVAILABLE_TOOLS}", tools_section)


def format_tools_documentation(tools: list[ToolMetadata]) -> str:
    """Format enabled tools into structured documentation.

    Groups tools by category and formats with descriptions and risk indicators.

    Args:
        tools: List of enabled tool metadata

    Returns:
        Formatted markdown documentation of available tools

    Example:
        >>> tools = [...]
        >>> doc = format_tools_documentation(tools)
        >>> "**File Operations:**" in doc
        True
    """
    if not tools:
        return _format_no_tools_message()

    # Categorize tools
    from consoul.ai.tools.base import ToolCategory

    categories: dict[str, list[ToolMetadata]] = {
        "File Operations": [],
        "Code Search & Analysis": [],
        "Web & Information": [],
        "System Execution": [],
        "Other": [],
    }

    for tool in tools:
        # Categorize based on tool categories or name patterns
        if tool.categories:
            if ToolCategory.FILE_EDIT in tool.categories:
                categories["File Operations"].append(tool)
            elif ToolCategory.SEARCH in tool.categories:
                categories["Code Search & Analysis"].append(tool)
            elif ToolCategory.WEB in tool.categories:
                categories["Web & Information"].append(tool)
            elif ToolCategory.EXECUTE in tool.categories:
                categories["System Execution"].append(tool)
            else:
                categories["Other"].append(tool)
        else:
            # Fallback to name-based categorization
            name_lower = tool.name.lower()
            if any(
                kw in name_lower
                for kw in ["file", "create", "edit", "delete", "append", "read_file"]
            ):
                categories["File Operations"].append(tool)
            elif any(kw in name_lower for kw in ["search", "grep", "code", "find"]):
                categories["Code Search & Analysis"].append(tool)
            elif any(kw in name_lower for kw in ["web", "url", "wikipedia"]):
                categories["Web & Information"].append(tool)
            elif "bash" in name_lower or "execute" in name_lower:
                categories["System Execution"].append(tool)
            else:
                categories["Other"].append(tool)

    # Build documentation
    lines = ["# Available Tools", "You have access to the following tools:\n"]

    for category_name, category_tools in categories.items():
        if not category_tools:
            continue

        lines.append(f"**{category_name}:**")
        for tool in sorted(category_tools, key=lambda t: t.name):
            # Format: - tool_name: description (risk indicator)
            risk_indicator = _get_risk_indicator(tool)
            lines.append(f"- {tool.name}: {tool.description}{risk_indicator}")

        lines.append("")  # Blank line between categories

    # Add usage guidelines
    lines.extend(
        [
            "# Tool Usage Guidelines",
            "1. **Always use tools when appropriate** - Don't just describe what to do, actually use the tools",
            '2. **For file listing**: Use bash_execute("ls") or bash_execute("find . -name \'*.py\'")',
            "3. **For searching code**: Use grep_search for patterns, code_search for definitions",
            '4. **For file content**: Use read_file, not bash_execute("cat")',
            "5. **Chain operations**: Use multiple tool calls to accomplish complex tasks",
        ]
    )

    return "\n".join(lines)


def _format_no_tools_message() -> str:
    """Format message when no tools are available.

    Returns:
        Message indicating no tools are enabled
    """
    return (
        "# Available Tools\n"
        "No tools are currently enabled. You can only provide text-based responses."
    )


def _get_risk_indicator(tool: ToolMetadata) -> str:
    """Get risk level indicator for tool documentation.

    Args:
        tool: Tool metadata

    Returns:
        Risk indicator string (e.g., " ⚠️ CAUTION", " 🚨 DANGEROUS")
    """
    from consoul.ai.tools.base import RiskLevel

    if tool.risk_level == RiskLevel.DANGEROUS:
        return " 🚨 DANGEROUS"
    elif tool.risk_level == RiskLevel.CAUTION:
        return " ⚠️ CAUTION"
    elif tool.risk_level == RiskLevel.BLOCKED:
        return " 🚫 BLOCKED"
    else:
        # SAFE - no indicator needed
        return ""
