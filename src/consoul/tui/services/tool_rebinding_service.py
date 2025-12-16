"""Tool rebinding service.

Handles rebinding tools to chat models after registry changes, including
model recreation and conversation updates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from consoul.ai import ConversationHistory
    from consoul.ai.tools import ToolRegistry
    from consoul.config import ConsoulConfig
    from consoul.config.models import ProfileConfig

import logging

logger = logging.getLogger(__name__)


class ToolRebindingService:
    """Handles tool rebinding operations for chat models.

    Args:
        tool_registry: Tool registry with enabled/disabled tools
        chat_model: Current chat model instance
        conversation: Optional conversation history
        consoul_config: Optional Consoul configuration
        active_profile: Optional active profile
        update_top_bar_callback: Callback to update top bar state
        build_system_prompt_callback: Callback to build system prompt
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        chat_model: Any,
        conversation: ConversationHistory | None = None,
        consoul_config: ConsoulConfig | None = None,
        active_profile: ProfileConfig | None = None,
        update_top_bar_callback: Callable[[], None] | None = None,
        build_system_prompt_callback: Callable[[], str | None] | None = None,
    ) -> None:
        """Initialize the tool rebinding service.

        Args:
            tool_registry: Tool registry with enabled/disabled tools
            chat_model: Current chat model instance
            conversation: Optional conversation history
            consoul_config: Optional Consoul configuration
            active_profile: Optional active profile
            update_top_bar_callback: Callback to update top bar state
            build_system_prompt_callback: Callback to build system prompt
        """
        self.tool_registry = tool_registry
        self.chat_model = chat_model
        self.conversation = conversation
        self.consoul_config = consoul_config
        self.active_profile = active_profile
        self.update_top_bar_callback = update_top_bar_callback
        self.build_system_prompt_callback = build_system_prompt_callback

    def rebind(self) -> Any:
        """Rebind tools to chat model after registry changes.

        Returns:
            Updated chat model with tools bound (or recreated without tools)

        Raises:
            Exception: If tool rebinding fails
        """
        from consoul.ai.providers import supports_tool_calling

        # Get currently enabled tools
        enabled_tools = self.tool_registry.list_tools(enabled_only=True)

        if enabled_tools and supports_tool_calling(self.chat_model):
            # Extract BaseTool instances
            tools = [meta.tool for meta in enabled_tools]

            # Rebind tools to model
            self.chat_model = self.chat_model.bind_tools(tools)

            logger.info(f"Rebound {len(tools)} tools to chat model")

            # Update conversation's model reference so it uses the rebound model
            if self.conversation:
                self.conversation._model = self.chat_model

            # Update top bar to reflect changes
            if self.update_top_bar_callback:
                self.update_top_bar_callback()

            # Update system prompt to reflect new tool availability
            self._update_system_prompt(len(enabled_tools))

        elif not enabled_tools:
            # No tools enabled - need to recreate model without tool bindings
            # LangChain doesn't provide an "unbind" method, so we recreate the model
            logger.info("No tools enabled - recreating model without tools")

            from consoul.ai import get_chat_model

            if self.consoul_config:
                model_config = self.consoul_config.get_current_model_config()
                self.chat_model = get_chat_model(
                    model_config, config=self.consoul_config
                )

                # Update conversation's model reference
                if self.conversation:
                    self.conversation._model = self.chat_model

                logger.info("Recreated model without tool bindings")

            # Update top bar to reflect changes
            if self.update_top_bar_callback:
                self.update_top_bar_callback()

            # Update system prompt to show no tools available
            self._update_system_prompt(0)

        return self.chat_model

    def _update_system_prompt(self, tool_count: int) -> None:
        """Update system prompt with new tool availability.

        Args:
            tool_count: Number of enabled tools
        """
        if not self.build_system_prompt_callback:
            return

        system_prompt = self.build_system_prompt_callback()
        if self.conversation is not None and system_prompt:
            self.conversation.clear(preserve_system=False)
            self.conversation.add_system_message(system_prompt)
            # Store updated prompt metadata
            self.conversation.store_system_prompt_metadata(
                profile_name=self.active_profile.name if self.active_profile else None,
                tool_count=tool_count,
            )
            logger.info(
                f"Updated system prompt with {'new' if tool_count > 0 else 'no'} tool availability"
            )
