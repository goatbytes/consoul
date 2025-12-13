"""System prompt builder service.

Handles construction of system prompts with environment context injection
and tool documentation replacement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.ai.tools import ToolRegistry
    from consoul.config.models import ProfileConfig

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

        Injects environment context (OS, working directory, git info) based on
        profile settings, then replaces {AVAILABLE_TOOLS} marker with dynamically
        generated tool documentation.

        Returns:
            Complete system prompt with environment context and tool docs, or None
        """
        from consoul.ai.environment import get_environment_context
        from consoul.ai.prompt_builder import build_system_prompt

        if not self.profile or not self.profile.system_prompt:
            return None

        # Start with base system prompt
        base_prompt = self.profile.system_prompt

        # Inject environment context if enabled
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

        if include_system or include_git:
            env_context = get_environment_context(
                include_system_info=include_system,
                include_git_info=include_git,
            )
            if env_context:
                # Prepend environment context to system prompt
                base_prompt = f"{env_context}\n\n{base_prompt}"
                logger.debug(f"Injected environment context ({len(env_context)} chars)")

        # Build final system prompt with tool documentation
        return build_system_prompt(base_prompt, self.tool_registry)
