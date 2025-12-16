"""Tool presets for quick workflow switching.

Provides built-in and custom tool presets that define collections of tools
for common workflows like code review, development, research, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.config.models import ToolPreset

__all__ = [
    "get_builtin_presets",
    "get_preset_tools",
    "list_available_presets",
    "resolve_preset",
]


def get_builtin_presets() -> dict[str, ToolPreset]:
    """Get built-in tool presets.

    Returns:
        Dictionary of built-in presets (name -> ToolPreset)

    Built-in presets:
        - readonly: Read-only tools for code review (grep, code_search, read, etc.)
        - development: Development tools (bash, file editing, search)
        - safe-research: Web research tools (web_search, wikipedia, read_url)
        - power-user: All available tools

    Example:
        >>> presets = get_builtin_presets()
        >>> assert "readonly" in presets
        >>> assert "development" in presets
    """
    from consoul.config.models import ToolPreset

    return {
        "readonly": ToolPreset(
            name="readonly",
            description="Read-only tools for code review and analysis",
            tools=[
                "grep",
                "code_search",
                "find_references",
                "read",
                "read_url",
                "web_search",
                "wikipedia",
            ],
        ),
        "development": ToolPreset(
            name="development",
            description="Development tools for file editing and execution",
            tools=[
                "bash",
                "grep",
                "code_search",
                "create_file",
                "edit_lines",
                "edit_replace",
                "append_file",
                "read",
            ],
        ),
        "safe-research": ToolPreset(
            name="safe-research",
            description="Web research and code reading tools",
            tools=[
                "web_search",
                "wikipedia",
                "read_url",
                "grep",
                "code_search",
                "read",
            ],
        ),
        "power-user": ToolPreset(
            name="power-user",
            description="All available tools (no restrictions)",
            tools=["all"],
        ),
    }


def list_available_presets(
    user_presets: dict[str, ToolPreset] | None = None,
) -> dict[str, ToolPreset]:
    """List all available presets (built-in + user-defined).

    Args:
        user_presets: Optional user-defined presets from config

    Returns:
        Dictionary of all presets (name -> ToolPreset)
        User presets override built-in presets with the same name

    Example:
        >>> presets = list_available_presets()
        >>> assert len(presets) >= 4  # At least 4 built-in presets
    """
    # Start with built-in presets
    all_presets = get_builtin_presets()

    # Merge user presets (user presets override built-in)
    if user_presets:
        all_presets.update(user_presets)

    return all_presets


def resolve_preset(
    preset_name: str, user_presets: dict[str, ToolPreset] | None = None
) -> list[str]:
    """Resolve a preset name to a list of tool specifications.

    Args:
        preset_name: Name of preset to resolve
        user_presets: Optional user-defined presets from config

    Returns:
        List of tool specifications (can be tool names, categories, "all", etc.)

    Raises:
        ValueError: If preset name is not found

    Example:
        >>> tools = resolve_preset("readonly")
        >>> assert "grep" in tools
        >>> assert "code_search" in tools
    """
    all_presets = list_available_presets(user_presets)

    preset_name_lower = preset_name.strip().lower()

    if preset_name_lower not in all_presets:
        available = ", ".join(sorted(all_presets.keys()))
        raise ValueError(
            f"Unknown preset '{preset_name}'. Available presets: {available}"
        )

    preset = all_presets[preset_name_lower]
    return preset.tools


def get_preset_tools(
    preset_name: str, user_presets: dict[str, ToolPreset] | None = None
) -> str:
    """Get tool specification string for a preset.

    Convenience function that converts preset tools list to comma-separated string
    for use with parse_and_resolve_tools().

    Args:
        preset_name: Name of preset
        user_presets: Optional user-defined presets from config

    Returns:
        Comma-separated tool specification string

    Raises:
        ValueError: If preset name is not found

    Example:
        >>> spec = get_preset_tools("readonly")
        >>> assert "grep" in spec
        >>> assert "," in spec  # Multiple tools
    """
    tools_list = resolve_preset(preset_name, user_presets)
    return ",".join(tools_list)
