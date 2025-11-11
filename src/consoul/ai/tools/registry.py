"""Tool registry for managing LangChain tools.

Provides centralized registration, configuration, and binding of tools
to LangChain chat models with security policy enforcement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from consoul.ai.tools.base import RiskLevel, ToolMetadata, get_tool_schema
from consoul.ai.tools.exceptions import ToolNotFoundError, ToolValidationError

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool

    from consoul.config.models import ToolConfig


class ToolRegistry:
    """Central registry for managing LangChain tools.

    Handles tool registration, configuration, security policy enforcement,
    and binding tools to chat models for tool calling.

    This registry is SDK-ready and works without TUI dependencies.

    Example:
        >>> from consoul.config.models import ToolConfig
        >>> from consoul.ai.tools import ToolRegistry, RiskLevel
        >>> from langchain_core.tools import tool
        >>>
        >>> @tool
        ... def my_tool(x: int) -> int:
        ...     '''Example tool'''
        ...     return x * 2
        >>>
        >>> config = ToolConfig(enabled=True, timeout=30)
        >>> registry = ToolRegistry(config)
        >>> registry.register(my_tool, risk_level=RiskLevel.SAFE)
        >>> tools_list = registry.list_tools()
        >>> assert len(tools_list) == 1
    """

    def __init__(self, config: ToolConfig):
        """Initialize tool registry with configuration.

        Args:
            config: ToolConfig instance controlling tool behavior
        """
        self.config = config
        self._tools: dict[str, ToolMetadata] = {}
        self._approved_this_session: set[str] = set()

    def register(
        self,
        tool: BaseTool,
        risk_level: RiskLevel = RiskLevel.SAFE,
        tags: list[str] | None = None,
        enabled: bool = True,
    ) -> None:
        """Register a LangChain tool in the registry.

        Args:
            tool: LangChain BaseTool instance (decorated with @tool)
            risk_level: Security risk classification for this tool
            tags: Optional tags for categorization
            enabled: Whether tool is enabled (overrides global config.enabled)

        Raises:
            ToolValidationError: If tool is invalid or already registered

        Example:
            >>> from langchain_core.tools import tool
            >>> @tool
            ... def bash_execute(command: str) -> str:
            ...     '''Execute bash command'''
            ...     return "output"
            >>> registry.register(bash_execute, risk_level=RiskLevel.DANGEROUS)
        """
        tool_name = tool.name

        # Validate tool
        if not tool_name or not tool_name.strip():
            raise ToolValidationError("Tool must have a non-empty name")

        if tool_name in self._tools:
            raise ToolValidationError(
                f"Tool '{tool_name}' is already registered. "
                "Unregister it first to re-register."
            )

        # Extract schema
        schema = get_tool_schema(tool)

        # Create metadata
        metadata = ToolMetadata(
            name=tool_name,
            description=tool.description or "",
            risk_level=risk_level,
            tool=tool,
            schema=schema,
            enabled=enabled and self.config.enabled,
            tags=tags,
        )

        self._tools[tool_name] = metadata

    def unregister(self, tool_name: str) -> None:
        """Remove a tool from the registry.

        Args:
            tool_name: Name of tool to unregister

        Raises:
            ToolNotFoundError: If tool is not registered
        """
        if tool_name not in self._tools:
            raise ToolNotFoundError(
                f"Tool '{tool_name}' not found in registry. "
                f"Available tools: {', '.join(self._tools.keys())}"
            )

        del self._tools[tool_name]

    def get_tool(self, tool_name: str) -> ToolMetadata:
        """Retrieve tool metadata by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            ToolMetadata instance for the requested tool

        Raises:
            ToolNotFoundError: If tool is not registered

        Example:
            >>> metadata = registry.get_tool("bash_execute")
            >>> assert metadata.risk_level == RiskLevel.DANGEROUS
        """
        if tool_name not in self._tools:
            available = ", ".join(self._tools.keys()) if self._tools else "none"
            raise ToolNotFoundError(
                f"Tool '{tool_name}' not found in registry. "
                f"Available tools: {available}"
            )

        return self._tools[tool_name]

    def list_tools(
        self,
        enabled_only: bool = False,
        risk_level: RiskLevel | None = None,
        tags: list[str] | None = None,
    ) -> list[ToolMetadata]:
        """List registered tools with optional filtering.

        Args:
            enabled_only: Only return enabled tools
            risk_level: Filter by risk level
            tags: Filter by tags (tool must have ALL specified tags)

        Returns:
            List of ToolMetadata instances matching filters

        Example:
            >>> safe_tools = registry.list_tools(risk_level=RiskLevel.SAFE)
            >>> enabled_tools = registry.list_tools(enabled_only=True)
        """
        tools = list(self._tools.values())

        if enabled_only:
            tools = [t for t in tools if t.enabled]

        if risk_level is not None:
            tools = [t for t in tools if t.risk_level == risk_level]

        if tags:
            tools = [t for t in tools if t.tags and all(tag in t.tags for tag in tags)]

        return tools

    def is_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed by security policy.

        Checks:
        1. Tool is registered
        2. Tool is enabled
        3. Tool is in allowed_tools whitelist (if whitelist is configured)

        Args:
            tool_name: Name of tool to check

        Returns:
            True if tool is allowed to execute, False otherwise

        Example:
            >>> config = ToolConfig(allowed_tools=["bash"])
            >>> registry = ToolRegistry(config)
            >>> registry.is_allowed("bash")  # True if registered and enabled
            >>> registry.is_allowed("python")  # False (not in whitelist)
        """
        # Check if tool exists
        if tool_name not in self._tools:
            return False

        metadata = self._tools[tool_name]

        # Check if tool is enabled
        if not metadata.enabled:
            return False

        # Check whitelist (empty whitelist = all tools allowed)
        return not (
            self.config.allowed_tools and tool_name not in self.config.allowed_tools
        )

    def needs_approval(self, tool_name: str) -> bool:
        """Determine if tool execution requires user approval.

        Based on approval_mode configuration:
        - 'always': Always require approval
        - 'once_per_session': Require approval on first use, then allow
        - 'whitelist': Only require approval for tools not in allowed_tools

        Args:
            tool_name: Name of tool to check

        Returns:
            True if approval is required, False otherwise

        Example:
            >>> config = ToolConfig(approval_mode="once_per_session")
            >>> registry = ToolRegistry(config)
            >>> registry.needs_approval("bash")  # True (first time)
            >>> registry.mark_approved("bash")
            >>> registry.needs_approval("bash")  # False (already approved)
        """
        # Auto-approve if configured (DANGEROUS!)
        if self.config.auto_approve:
            return False

        # Always mode: always require approval
        if self.config.approval_mode == "always":
            return True

        # Once per session: require approval if not yet approved
        if self.config.approval_mode == "once_per_session":
            return tool_name not in self._approved_this_session

        # Whitelist mode: only require approval for non-whitelisted tools
        if self.config.approval_mode == "whitelist":
            return tool_name not in self.config.allowed_tools

        # Default: require approval
        return True

    def mark_approved(self, tool_name: str) -> None:
        """Mark a tool as approved for this session.

        Used with 'once_per_session' approval mode to track which tools
        have been approved by the user.

        Args:
            tool_name: Name of tool to mark as approved
        """
        self._approved_this_session.add(tool_name)

    def assess_risk(self, tool_name: str, arguments: dict[str, Any]) -> RiskLevel:
        """Assess risk level for a tool execution.

        Returns the tool's configured risk level. Can be overridden by
        subclasses to implement dynamic risk assessment based on arguments.

        Args:
            tool_name: Name of tool being executed
            arguments: Arguments that will be passed to tool

        Returns:
            RiskLevel for this execution

        Raises:
            ToolNotFoundError: If tool is not registered

        Example:
            >>> risk = registry.assess_risk("bash_execute", {"command": "ls"})
            >>> assert risk == RiskLevel.DANGEROUS  # bash is always dangerous
        """
        metadata = self.get_tool(tool_name)
        return metadata.risk_level

    def bind_to_model(
        self,
        model: BaseChatModel,
        tool_names: list[str] | None = None,
    ) -> BaseChatModel:
        """Bind registered tools to a LangChain chat model.

        This enables the model to call tools via the tool calling API.

        Args:
            model: LangChain BaseChatModel instance
            tool_names: Optional list of specific tools to bind (default: all enabled tools)

        Returns:
            Model with tools bound (via bind_tools())

        Raises:
            ToolNotFoundError: If a requested tool is not registered

        Example:
            >>> from consoul.ai import get_chat_model
            >>> chat_model = get_chat_model("claude-3-5-sonnet-20241022")
            >>> model_with_tools = registry.bind_to_model(chat_model)
            >>> # Model can now request tool executions
        """
        # Determine which tools to bind
        if tool_names is None:
            # Bind all enabled and allowed tools
            tools_to_bind = [
                metadata.tool
                for metadata in self.list_tools(enabled_only=True)
                if self.is_allowed(metadata.name)
            ]
        else:
            # Bind specific tools
            tools_to_bind = []
            for tool_name in tool_names:
                metadata = self.get_tool(tool_name)
                if metadata.enabled and self.is_allowed(tool_name):
                    tools_to_bind.append(metadata.tool)

        # Bind tools to model if any are available
        if tools_to_bind:
            return model.bind_tools(tools_to_bind)

        return model

    def get_tool_by_id(self, tool_call_id: str) -> ToolMetadata | None:
        """Get tool metadata by tool call ID.

        This is a placeholder for future functionality where we might track
        tool call IDs from AI messages. For now, returns None.

        Args:
            tool_call_id: Tool call ID from AIMessage.tool_calls

        Returns:
            ToolMetadata if found, None otherwise
        """
        # TODO: Implement tool call ID tracking in SOUL-61
        return None

    def clear_session_approvals(self) -> None:
        """Clear all session-based approvals.

        Resets the 'once_per_session' approval tracking, requiring
        re-approval for all tools.

        Useful for:
        - Starting a new conversation
        - Security reset after sensitive operations
        - Testing approval workflows
        """
        self._approved_this_session.clear()

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools

    def __repr__(self) -> str:
        """Return string representation of registry."""
        enabled = sum(1 for t in self._tools.values() if t.enabled)
        return (
            f"ToolRegistry(tools={len(self._tools)}, "
            f"enabled={enabled}, "
            f"approval_mode='{self.config.approval_mode}')"
        )
