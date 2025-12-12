"""ToolService - Tool management and execution service.

Encapsulates tool setup, configuration, and execution logic.
Provides SDK-layer interface for tool management without UI dependencies.

Extracted from ConsoulApp (tui/app.py) to enable headless tool usage.

Example:
    >>> from consoul.sdk.services import ToolService
    >>> service = ToolService.from_config(config)
    >>> tools = service.list_tools(enabled_only=True)
    >>> needs_approval = service.needs_approval("bash_execute", {"command": "ls"})
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.ai.tools import ToolRegistry
    from consoul.config import ConsoulConfig
    from consoul.config.models import ToolConfig

logger = logging.getLogger(__name__)

__all__ = ["ToolService"]


class ToolService:
    """Service layer for tool management and execution.

    Encapsulates ToolRegistry and provides clean interface for:
    - Tool configuration and registration
    - Tool listing and metadata
    - Approval policy checks

    Attributes:
        tool_registry: ToolRegistry instance managing tool catalog
        config: Tool configuration settings

    Example - Basic usage:
        >>> service = ToolService.from_config(config)
        >>> tools = service.list_tools()
        >>> for tool in tools:
        ...     print(f"{tool.name}: {tool.description}")

    Example - Check approval:
        >>> needs_approval = service.needs_approval("bash_execute", {"command": "ls"})
        >>> if needs_approval:
        ...     # Show approval modal
        ...     pass
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        config: ToolConfig | None = None,
    ) -> None:
        """Initialize tool service.

        Args:
            tool_registry: Configured ToolRegistry instance
            config: Tool configuration settings
        """
        self.tool_registry = tool_registry
        self.config = config

    @classmethod
    def from_config(cls, config: ConsoulConfig) -> ToolService:
        """Create ToolService from configuration.

        Factory method that initializes ToolRegistry with tool configuration,
        enabling/disabling based on config settings, and registering all tools.

        Extracted from ConsoulApp._initialize_tool_registry() (lines 433-612).

        Args:
            config: Consoul configuration with tool settings

        Returns:
            Initialized ToolService ready for use

        Example:
            >>> from consoul.config import load_config
            >>> config = load_config()
            >>> service = ToolService.from_config(config)
        """
        from consoul.ai.tools import ToolRegistry
        from consoul.ai.tools.catalog import (
            TOOL_CATALOG,
            get_all_tool_names,
            get_tool_by_name,
            get_tools_by_risk_level,
        )
        from consoul.ai.tools.implementations import (
            set_analyze_images_config,
            set_bash_config,
            set_code_search_config,
            set_file_edit_config,
            set_find_references_config,
            set_grep_search_config,
            set_read_config,
            set_read_url_config,
            set_web_search_config,
            set_wikipedia_config,
        )
        from consoul.ai.tools.providers import CliApprovalProvider

        # Configure bash tool with profile settings
        if config.tools.bash:
            set_bash_config(config.tools.bash)

        # Configure read tool with profile settings
        if config.tools.read:
            set_read_config(config.tools.read)

        # Configure grep_search tool with profile settings
        if config.tools.grep_search:
            set_grep_search_config(config.tools.grep_search)

        # Configure code_search tool with profile settings
        if config.tools.code_search:
            set_code_search_config(config.tools.code_search)

        # Configure find_references tool with profile settings
        if config.tools.find_references:
            set_find_references_config(config.tools.find_references)

        # Configure web_search tool with profile settings
        if config.tools.web_search:
            set_web_search_config(config.tools.web_search)

        # Configure wikipedia_search tool with profile settings
        if config.tools.wikipedia:
            set_wikipedia_config(config.tools.wikipedia)

        # Configure read_url tool with profile settings
        if config.tools.read_url:
            set_read_url_config(config.tools.read_url)

        # Configure file_edit tool with profile settings
        if config.tools.file_edit:
            set_file_edit_config(config.tools.file_edit)

        # Configure image_analysis tool with profile settings
        if config.tools.image_analysis:
            set_analyze_images_config(config.tools.image_analysis)

        # Determine which tools to register based on config
        # Note: We always register ALL tools in the registry so Tool Manager can show them all
        # The enabled/disabled state is set based on config (allowed_tools, risk_filter, or default)

        # Get all available tools
        all_tools = list(TOOL_CATALOG.values())

        # Determine which tools should be ENABLED based on config
        # Precedence: allowed_tools > risk_filter > all tools (default)
        enabled_tool_names = set()  # Set of tool.name values that should be enabled

        if config.tools.allowed_tools is not None:
            # Explicit whitelist takes precedence (even if empty)
            normalized_tool_names = []  # Actual tool.name values for registry
            invalid_tools = []

            for tool_name in config.tools.allowed_tools:
                result = get_tool_by_name(tool_name)
                if result:
                    tool, risk_level, _categories = result
                    # Store the actual tool.name for execution whitelist
                    normalized_tool_names.append(tool.name)
                    enabled_tool_names.add(tool.name)
                else:
                    invalid_tools.append(tool_name)

            # Error if any invalid tool names
            if invalid_tools:
                available = get_all_tool_names()
                raise ValueError(
                    f"Invalid tool names in allowed_tools: {invalid_tools}. "
                    f"Available tools: {available}"
                )

            # Normalize allowed_tools to actual tool.name values for execution checks
            # This ensures friendly names like "bash" work with ToolRegistry.is_allowed()
            # which checks against tool.name like "bash_execute"
            config.tools.allowed_tools = normalized_tool_names

            logger.info(
                f"Enabled {len(enabled_tool_names)} tools from allowed_tools "
                f"{'(chat-only mode)' if len(enabled_tool_names) == 0 else 'whitelist'}"
            )

        elif config.tools.risk_filter:
            # Risk-based filtering: enable tools up to specified risk level
            tools_by_risk = get_tools_by_risk_level(config.tools.risk_filter)

            # Enable tools that match risk filter
            for tool, _risk_level, _categories in tools_by_risk:
                enabled_tool_names.add(tool.name)

            # DO NOT populate allowed_tools - leave empty for risk_filter.
            #
            # Why: Populating allowed_tools would bypass risk-based approval workflow.
            # The approval flow checks _is_whitelisted() BEFORE checking risk levels,
            # so adding all filtered tools to allowed_tools would auto-approve them
            # regardless of permission_policy settings (src/consoul/ai/tools/permissions/policy.py:307).
            #
            # Security model:
            # - risk_filter controls which tools are ENABLED
            # - permission_policy controls APPROVAL (which tools need confirmation)
            # - Both work together: risk_filter limits capabilities, policy controls UX
            #
            # Example: risk_filter="caution" + permission_policy="balanced"
            # - Enables: SAFE + CAUTION tools (12 total)
            # - Auto-approves: SAFE tools only
            # - Prompts for: CAUTION tools (file edits, bash, etc.)
            #
            # Note: risk_filter is incompatible with approval_mode="whitelist".
            # Use permission_policy (BALANCED/TRUSTING/etc) instead.

            logger.info(
                f"Enabled {len(enabled_tool_names)} tools with "
                f"risk_filter='{config.tools.risk_filter}'"
            )

        else:
            # Default: enable all tools (backward compatible)
            for tool, _risk_level, _categories in all_tools:
                enabled_tool_names.add(tool.name)

            logger.info(
                f"Enabled all {len(enabled_tool_names)} available tools (no filters specified)"
            )

        # Create registry with CLI provider (may be overridden by callers)
        # The provider is required by registry but callers can provide their own approval
        # NOTE: If allowed_tools was specified, it has been normalized to actual tool names
        tool_registry = ToolRegistry(
            config=config.tools,
            approval_provider=CliApprovalProvider(),  # Default provider
        )

        # Register ALL tools with appropriate enabled state
        # This ensures Tool Manager shows all available tools (not just enabled ones)
        for tool, risk_level, _categories in all_tools:
            # Tool is enabled if its name is in the enabled_tool_names set
            is_enabled = tool.name in enabled_tool_names
            tool_registry.register(tool, risk_level=risk_level, enabled=is_enabled)

        # Get tool metadata list for logging
        tool_metadata_list = tool_registry.list_tools(enabled_only=True)

        logger.info(
            f"Initialized tool registry with {len(tool_metadata_list)} enabled tools"
        )

        return cls(tool_registry=tool_registry, config=config.tools)

    def list_tools(
        self,
        enabled_only: bool = True,
        category: str | None = None,
    ) -> list[Any]:
        """List available tools.

        Args:
            enabled_only: If True, only return enabled tools
            category: Optional category filter

        Returns:
            List of ToolMetadata objects

        Example:
            >>> tools = service.list_tools(enabled_only=True)
            >>> for tool in tools:
            ...     print(f"{tool.name}: {tool.description}")
        """
        # For now, delegate to ToolRegistry
        # Future: Return simple dataclasses instead of ToolMetadata
        return self.tool_registry.list_tools(enabled_only=enabled_only)

    def needs_approval(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Check if tool needs approval based on policy.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments dict

        Returns:
            True if approval is needed, False if auto-approved

        Example:
            >>> if service.needs_approval("bash_execute", {"command": "ls"}):
            ...     # Show approval modal
            ...     approved = await show_approval_modal()
        """
        return self.tool_registry.needs_approval(tool_name, arguments)

    def get_tools_count(self) -> int:
        """Get total number of registered tools.

        Returns:
            Total number of tools in registry

        Example:
            >>> total = service.get_tools_count()
            >>> print(f"Total tools: {total}")
        """
        all_tools = self.tool_registry.list_tools(enabled_only=False)
        return len(all_tools)
