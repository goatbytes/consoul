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
    auto_append_tools: bool = True,
) -> str | None:
    """Build system prompt with dynamic tool documentation.

    Replaces the {AVAILABLE_TOOLS} marker in the base prompt with a dynamically
    generated tools section based on currently enabled tools.

    If no marker is present but tools are available, appends tools section to end
    (controlled by auto_append_tools parameter).

    Args:
        base_prompt: Base system prompt template (may contain {AVAILABLE_TOOLS})
        tool_registry: Tool registry to query for enabled tools (optional)
        auto_append_tools: If False, only replace {AVAILABLE_TOOLS} marker,
                          don't auto-append when marker is absent (default: True)

    Returns:
        Complete system prompt with tool documentation, or None if no base prompt

    Example:
        >>> # With marker (always replaced regardless of auto_append_tools)
        >>> prompt = build_system_prompt(
        ...     "You are an AI assistant.\\n\\n{AVAILABLE_TOOLS}",
        ...     tool_registry
        ... )
        >>> "bash_execute" in prompt
        True

        >>> # Without marker (auto-append enabled - default behavior)
        >>> prompt = build_system_prompt(
        ...     "You are an AI assistant.",
        ...     tool_registry  # has tools
        ... )
        >>> "# Available Tools" in prompt
        True

        >>> # Without marker (auto-append disabled - SDK use case)
        >>> prompt = build_system_prompt(
        ...     "You are an AI assistant.",
        ...     tool_registry,  # has tools
        ...     auto_append_tools=False
        ... )
        >>> "# Available Tools" in prompt
        False
    """
    if not base_prompt:
        return None

    # Build tools section if registry exists
    tools_section = None
    if tool_registry:
        enabled_tools = tool_registry.list_tools(enabled_only=True)
        if enabled_tools:
            tools_section = format_tools_documentation(enabled_tools)

    # Strategy 1: Replace marker if present (always, regardless of auto_append_tools)
    if "{AVAILABLE_TOOLS}" in base_prompt:
        if tools_section:
            return base_prompt.replace("{AVAILABLE_TOOLS}", tools_section)
        else:
            # No tools - replace with "no tools" message
            return base_prompt.replace("{AVAILABLE_TOOLS}", _format_no_tools_message())

    # Strategy 2: Smart fallback - append tools ONLY if auto_append_tools is True
    if auto_append_tools and tools_section:
        # Append tools section to end (for profiles without explicit marker)
        return f"{base_prompt}\n\n{tools_section}"

    # Strategy 3: No marker, auto-append disabled, or no tools - return as-is
    return base_prompt


def build_enhanced_system_prompt(
    base_prompt: str | None,
    tool_registry: ToolRegistry | None = None,
    include_env_context: bool = True,
    include_git_context: bool = True,
    auto_append_tools: bool = True,
) -> str | None:
    """Build system prompt with full control over all injections.

    One-stop function for comprehensive prompt building with control over
    environment context, git info, and tool documentation. Perfect for SDK
    users who want fine-grained control.

    Args:
        base_prompt: Base system prompt template (may contain {AVAILABLE_TOOLS})
        tool_registry: Optional tool registry for tool documentation
        include_env_context: Include OS/shell/working directory info (default: True)
        include_git_context: Include git repository info (default: True)
        auto_append_tools: Auto-append tool docs if no marker present (default: True)

    Returns:
        Complete system prompt with requested injections, or None if no base prompt

    Example - SDK user with full control:
        >>> # Tools enabled but no docs, no env context
        >>> prompt = build_enhanced_system_prompt(
        ...     "You are an AI assistant.",
        ...     tool_registry=my_registry,
        ...     include_env_context=False,
        ...     include_git_context=False,
        ...     auto_append_tools=False,
        ... )
        >>> prompt == "You are an AI assistant."
        True

    Example - CLI/TUI default behavior:
        >>> # Everything enabled (current behavior)
        >>> prompt = build_enhanced_system_prompt(
        ...     "You are an AI assistant.",
        ...     tool_registry=my_registry,
        ... )
        >>> "Working Directory:" in prompt
        True
        >>> "# Available Tools" in prompt
        True

    Example - Custom tool doc placement:
        >>> # Use marker for control
        >>> prompt = build_enhanced_system_prompt(
        ...     "Assistant\\n\\n{AVAILABLE_TOOLS}\\n\\nContext:",
        ...     tool_registry=my_registry,
        ...     include_env_context=False,
        ... )
        >>> "# Available Tools" in prompt
        True
        >>> "{AVAILABLE_TOOLS}" not in prompt
        True
    """
    if not base_prompt:
        return None

    # Inject environment context if requested
    if include_env_context or include_git_context:
        from consoul.ai.environment import get_environment_context

        env_context = get_environment_context(
            include_system_info=include_env_context,
            include_git_info=include_git_context,
        )
        if env_context:
            # Prepend environment context to system prompt
            base_prompt = f"{env_context}\n\n{base_prompt}"

    # Build final prompt with tool documentation
    return build_system_prompt(
        base_prompt, tool_registry, auto_append_tools=auto_append_tools
    )


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
        "# Available Tools\n\n"
        "**You have NO tools available.**\n\n"
        "When asked about your capabilities or what tools you have:\n"
        "- Respond: 'I currently have no tools enabled. I can only provide text-based responses.'\n"
        "- Do NOT list or describe hypothetical tools\n"
        "- Do NOT mention bash, file operations, search capabilities, or any other tool features\n\n"
        "If asked to perform actions (read files, execute commands, search code):\n"
        "- Respond: 'I cannot perform that action - all tools are disabled. Enable tools via the Tool Manager first.'\n\n"
        "You are limited to conversational responses only."
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
