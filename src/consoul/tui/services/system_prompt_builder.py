"""System prompt builder service.

Handles construction of system prompts with environment context injection
and tool documentation replacement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.ai.tools import ToolRegistry
    from consoul.tui.profiles import ProfileConfig

import logging

logger = logging.getLogger(__name__)


class SystemPromptBuilder:
    """Builds system prompts with environment context and tool documentation.

    Args:
        profile: Active profile configuration
        tool_registry: Optional tool registry for tool documentation
    """

    def __init__(
        self,
        profile: ProfileConfig,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        """Initialize the system prompt builder.

        Args:
            profile: Active profile configuration
            tool_registry: Optional tool registry for tool documentation
        """
        self.profile = profile
        self.tool_registry = tool_registry

    def build(self) -> str | None:
        """Build complete system prompt with context and tool docs.

        Delegates to SDK's build_enhanced_system_prompt() for consistency.

        Returns:
            Complete system prompt with environment context and tool docs, or None
        """
        from consoul.ai.prompt_builder import build_enhanced_system_prompt

        if not self.profile or not self.profile.system_prompt:
            return None

        # Get context settings from profile
        include_system = (
            self.profile.context.include_system_info
            if hasattr(self.profile, "context")
            else True
        )
        include_git = (
            self.profile.context.include_git_info
            if hasattr(self.profile, "context")
            else True
        )
        include_tools = (
            self.profile.context.include_tools
            if hasattr(self.profile, "context")
            and hasattr(self.profile.context, "include_tools")
            else True
        )

        # Use SDK builder with profile-controlled tool appending
        return build_enhanced_system_prompt(
            base_prompt=self.profile.system_prompt,
            tool_registry=self.tool_registry if include_tools else None,
            include_env_context=include_system,
            include_git_context=include_git,
            auto_append_tools=include_tools,
        )
