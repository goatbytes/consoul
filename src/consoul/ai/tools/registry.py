"""Tool registry for managing LangChain tools.

Provides centralized registration, configuration, and binding of tools
to LangChain chat models with security policy enforcement.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from consoul.ai.tools.approval import (
    ApprovalProvider,
    ToolApprovalRequest,
    ToolApprovalResponse,
)
from consoul.ai.tools.audit import (
    AuditEvent,
    AuditLogger,
    FileAuditLogger,
    NullAuditLogger,
)
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

    IMPORTANT - Approval Workflow Coordination:
        The registry provides approval caching (once_per_session mode) but does
        NOT handle user approval itself. You must implement an ApprovalProvider
        (see SOUL-66) that:

        1. Checks registry.needs_approval(tool_name)
        2. If True: Shows approval UI and gets user decision
        3. If approved: Calls registry.mark_approved(tool_name)
        4. Executes the tool

        The registry-level caching is an optimization to avoid showing the
        approval modal multiple times for the same tool. It does NOT replace
        the approval provider.

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

    def __init__(
        self,
        config: ToolConfig,
        approval_provider: ApprovalProvider | None = None,
        audit_logger: AuditLogger | None = None,
    ):
        """Initialize tool registry with configuration.

        Args:
            config: ToolConfig instance controlling tool behavior
            approval_provider: Optional approval provider for tool execution.
                If None, will attempt to use TuiApprovalProvider (if TUI available)
                or raise error if no provider available.
            audit_logger: Optional audit logger for tool execution tracking.
                If None, creates FileAuditLogger or NullAuditLogger based on config.
        """
        self.config = config
        self._tools: dict[str, ToolMetadata] = {}
        self._approved_this_session: set[str] = set()
        self.approval_provider = approval_provider or self._get_default_provider()
        self.audit_logger = audit_logger or self._create_audit_logger()

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

    def needs_approval(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> bool:
        """Determine if tool execution requires user approval.

        IMPORTANT: This method checks registry-level approval caching ONLY.
        It does NOT invoke the approval provider (see SOUL-66). The approval
        provider must check needs_approval() first, then show approval UI if needed.

        Workflow:
        1. Approval provider calls registry.needs_approval(tool_name, arguments)
        2. If True: Show approval modal/prompt, get user decision
        3. If user approves: Call registry.mark_approved(tool_name)
        4. Execute tool

        Based on approval_mode/permission_policy configuration:
        - 'always': Always require approval (PARANOID policy)
        - 'risk_based': Based on risk level vs threshold (BALANCED/TRUSTING policies)
        - 'once_per_session': Require approval on first use, then cache approval
        - 'whitelist': Only require approval for tools not in allowed_tools
        - 'never': Never require approval (UNRESTRICTED policy - DANGEROUS)

        Special handling for bash_execute:
        - Checks command-level whitelist from BashToolConfig.whitelist_patterns
        - Whitelisted commands bypass approval even in 'always' mode

        Args:
            tool_name: Name of tool to check
            arguments: Optional tool arguments (used for command-level whitelist and risk assessment)

        Returns:
            True if approval UI should be shown, False if cached/whitelisted

        Example:
            >>> config = ToolConfig(approval_mode="once_per_session")
            >>> registry = ToolRegistry(config)
            >>> registry.needs_approval("bash_execute")  # True (first time)
            >>> # ... approval provider shows modal, user approves ...
            >>> registry.mark_approved("bash_execute")
            >>> registry.needs_approval("bash_execute")  # False (cached, skip modal)
            >>>
            >>> # Command-level whitelist
            >>> config = ToolConfig(bash=BashToolConfig(whitelist_patterns=["git status"]))
            >>> registry.needs_approval("bash_execute", {"command": "git status"})  # False (whitelisted)
            >>>
            >>> # Risk-based approval (BALANCED policy)
            >>> from consoul.ai.tools.permissions import PermissionPolicy
            >>> config = ToolConfig(permission_policy=PermissionPolicy.BALANCED)
            >>> registry = ToolRegistry(config)
            >>> # SAFE commands auto-approved, CAUTION+ require approval

        Warning:
            Never execute tools when needs_approval() returns True without
            going through the approval provider first. The registry-level
            caching is an optimization, not a replacement for user approval.
        """
        # Use PolicyResolver if permission_policy is set
        if (
            hasattr(self.config, "permission_policy")
            and self.config.permission_policy is not None
        ):
            from consoul.ai.tools.permissions.policy import PolicyResolver

            resolver = PolicyResolver(self.config)
            settings = resolver.get_effective_settings()

            # Check whitelist first (highest priority)
            if resolver._is_whitelisted(tool_name, arguments):
                return False

            # Handle 'never' mode (UNRESTRICTED policy)
            if settings.approval_mode == "never":
                return False

            # Handle 'always' mode (PARANOID policy)
            if settings.approval_mode == "always":
                return True

            # Handle 'risk_based' mode (BALANCED/TRUSTING policies)
            if settings.approval_mode == "risk_based":
                # Get risk assessment for this tool/command
                risk_assessment = self.assess_risk(tool_name, arguments or {})

                # Extract risk level from CommandRisk or RiskLevel
                if hasattr(risk_assessment, "level"):
                    risk_level = risk_assessment.level
                else:
                    risk_level = risk_assessment

                # Use PolicyResolver to determine if approval is needed
                return resolver.should_require_approval(
                    tool_name, risk_level, arguments
                )

            # For other modes, fall through to legacy logic below

        # Legacy approval logic (for backward compatibility when policy is None)

        # Auto-approve if configured (DANGEROUS!)
        if self.config.auto_approve:
            return False

        # For bash_execute, check command-level whitelist
        if tool_name == "bash_execute" and arguments and "command" in arguments:
            from consoul.ai.tools.implementations.bash import is_whitelisted

            if is_whitelisted(arguments["command"], self.config.bash):
                return False  # Whitelisted command bypasses approval

        # Always mode: always require approval
        if self.config.approval_mode == "always":
            return True

        # Once per session: require approval if not yet approved
        if self.config.approval_mode == "once_per_session":
            return tool_name not in self._approved_this_session

        # Whitelist mode: only require approval for non-whitelisted tools
        if self.config.approval_mode == "whitelist":
            return tool_name not in self.config.allowed_tools

        # Risk-based mode (manual config)
        if self.config.approval_mode == "risk_based":
            # Get risk assessment
            risk_assessment = self.assess_risk(tool_name, arguments or {})
            if hasattr(risk_assessment, "level"):
                risk_level = risk_assessment.level
            else:
                risk_level = risk_assessment

            # Default threshold for manual config is SAFE
            # (auto-approve SAFE, require approval for CAUTION+)
            risk_values = {"safe": 0, "caution": 1, "dangerous": 2, "blocked": 3}
            tool_risk_value = risk_values.get(risk_level.value, 3)
            threshold_value = risk_values.get(RiskLevel.SAFE.value, 0)
            return tool_risk_value > threshold_value

        # Never mode (manual config - DANGEROUS) or default: require approval
        return self.config.approval_mode != "never"

    def mark_approved(self, tool_name: str) -> None:
        """Mark a tool as approved for this session.

        IMPORTANT: This method should ONLY be called by the approval provider
        AFTER the user has explicitly approved the tool execution. Never call
        this method directly without user approval.

        Used with 'once_per_session' approval mode to cache approval decisions
        so the user doesn't need to approve the same tool multiple times in
        one session.

        Args:
            tool_name: Name of tool to mark as approved

        Warning:
            Calling this method bypasses the approval UI for future executions
            of this tool in the current session. Only call after explicit user
            approval through the approval provider (SOUL-66).

        Example:
            >>> # In approval provider implementation:
            >>> if registry.needs_approval("bash"):
            ...     user_approved = show_approval_modal("bash", args)
            ...     if user_approved:
            ...         registry.mark_approved("bash")  # Cache approval
            ...         # Now execute tool
        """
        self._approved_this_session.add(tool_name)

    def assess_risk(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Assess risk level for a tool execution.

        For bash_execute tool, performs dynamic risk assessment using CommandAnalyzer.
        For other tools, returns static risk level from metadata.

        Args:
            tool_name: Name of tool being executed
            arguments: Arguments that will be passed to tool

        Returns:
            CommandRisk for bash_execute (with level, reason, suggestions)
            RiskLevel for other tools (static level)

        Raises:
            ToolNotFoundError: If tool is not registered

        Example:
            >>> # Dynamic assessment for bash
            >>> risk = registry.assess_risk("bash_execute", {"command": "ls"})
            >>> assert risk.level == RiskLevel.SAFE
            >>> assert "read-only" in risk.reason.lower()
            >>>
            >>> # Static assessment for other tools
            >>> risk = registry.assess_risk("other_tool", {})
            >>> assert isinstance(risk, RiskLevel)
        """
        from consoul.ai.tools.permissions.analyzer import CommandAnalyzer, CommandRisk

        metadata = self.get_tool(tool_name)

        # For bash_execute tool, use CommandAnalyzer for dynamic assessment
        if tool_name == "bash_execute" and "command" in arguments:
            analyzer = CommandAnalyzer()
            return analyzer.analyze_command(arguments["command"])

        # For other tools, return static risk level wrapped in CommandRisk
        return CommandRisk(
            level=metadata.risk_level,
            reason=f"Static risk level for {tool_name}",
            matched_pattern=None,
        )

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

    def _create_audit_logger(self) -> AuditLogger:
        """Create audit logger based on configuration.

        Returns:
            FileAuditLogger if audit_logging is enabled, NullAuditLogger otherwise.

        Example:
            >>> config = ToolConfig(audit_logging=True)
            >>> registry = ToolRegistry(config)
            >>> # Uses FileAuditLogger at ~/.consoul/tool_audit.jsonl
            >>>
            >>> config = ToolConfig(audit_logging=False)
            >>> registry = ToolRegistry(config)
            >>> # Uses NullAuditLogger (no-op)
        """
        if self.config.audit_logging:
            return FileAuditLogger(self.config.audit_log_file)
        return NullAuditLogger()

    def _get_default_provider(self) -> ApprovalProvider:
        """Get default approval provider.

        Note: This method cannot create TuiApprovalProvider since it requires
        an app instance. TUI applications should explicitly provide the provider.

        Raises:
            RuntimeError: Always raised, indicating provider is required

        Example:
            # TUI app should provide provider:
            >>> from consoul.tui.tools import TuiApprovalProvider
            >>> provider = TuiApprovalProvider(app)
            >>> registry = ToolRegistry(config, approval_provider=provider)
            >>>
            # CLI/SDK should provide provider:
            >>> from consoul.ai.tools.providers import CliApprovalProvider
            >>> provider = CliApprovalProvider()
            >>> registry = ToolRegistry(config, approval_provider=provider)
        """
        raise RuntimeError(
            "No approval provider specified. "
            "ToolRegistry requires an explicit approval_provider. "
            "Examples:\n\n"
            "  # For TUI applications:\n"
            "  from consoul.tui.tools import TuiApprovalProvider\n"
            "  provider = TuiApprovalProvider(app)\n"
            "  registry = ToolRegistry(config, approval_provider=provider)\n\n"
            "  # For CLI/SDK applications:\n"
            "  from consoul.ai.tools.providers import CliApprovalProvider\n"
            "  provider = CliApprovalProvider()\n"
            "  registry = ToolRegistry(config, approval_provider=provider)"
        )

    async def request_tool_approval(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tool_call_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> ToolApprovalResponse:
        """Request approval for tool execution.

        Coordinates with approval provider and registry-level caching.

        Workflow:
        1. Check if approval needed (via needs_approval)
        2. If cached/whitelisted: Auto-approve
        3. Otherwise: Call approval provider
        4. If approved: Mark as approved for session
        5. Return response

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments
            tool_call_id: Unique tool call ID from AI message
            context: Additional context for approval provider

        Returns:
            ToolApprovalResponse with decision

        Raises:
            ToolNotFoundError: If tool not registered

        Example:
            >>> response = await registry.request_tool_approval(
            ...     "bash_execute",
            ...     {"command": "ls -la"},
            ...     tool_call_id="call_123"
            ... )
            >>> if response.approved:
            ...     # Execute tool
            ...     pass
        """
        # Get tool metadata
        metadata = self.get_tool(tool_name)

        # Start timing for audit log
        start_time = time.time()

        # Log approval request
        await self.audit_logger.log_event(
            AuditEvent(
                event_type="request",
                tool_name=tool_name,
                arguments=arguments,
                metadata=context or {},
            )
        )

        # Check if approval needed (registry-level caching)
        if not self.needs_approval(tool_name, arguments):
            # Auto-approved (cached or whitelisted)
            duration_ms = int((time.time() - start_time) * 1000)
            await self.audit_logger.log_event(
                AuditEvent(
                    event_type="approval",
                    tool_name=tool_name,
                    arguments=arguments,
                    decision=True,
                    result="Auto-approved (cached or whitelisted)",
                    duration_ms=duration_ms,
                    metadata=context or {},
                )
            )
            return ToolApprovalResponse(
                approved=True,
                reason="Auto-approved (cached or whitelisted)",
            )

        # For file edit tools with dry_run support, generate preview first
        preview = None
        file_edit_tools = {"create_file", "delete_file", "append_to_file"}
        if tool_name in file_edit_tools:
            try:
                # Create dry_run arguments
                dry_run_args = arguments.copy()
                dry_run_args["dry_run"] = True

                # Invoke tool with dry_run=True to get preview
                result_str = metadata.tool.invoke(dry_run_args)

                # Parse result to extract preview
                import json as json_module

                result_data = json_module.loads(result_str)
                if "preview" in result_data:
                    preview = result_data["preview"]
            except Exception:
                # If preview generation fails, continue without preview
                # (approval will still work, just without diff visualization)
                pass

        # Build approval request
        request = ToolApprovalRequest(
            tool_name=tool_name,
            arguments=arguments,
            risk_level=metadata.risk_level,
            tool_call_id=tool_call_id,
            description=metadata.description,
            preview=preview,
            context=context or {},
        )

        # Request approval from provider
        try:
            response = await self.approval_provider.request_approval(request)

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log approval/denial event
            await self.audit_logger.log_event(
                AuditEvent(
                    event_type="approval" if response.approved else "denial",
                    tool_name=tool_name,
                    arguments=arguments,
                    decision=response.approved,
                    result=response.reason,
                    duration_ms=duration_ms,
                    metadata=context or {},
                )
            )

            # If approved, mark for session caching
            if response.approved:
                self.mark_approved(tool_name)

            return response

        except Exception as e:
            # Approval provider error - treat as denial
            duration_ms = int((time.time() - start_time) * 1000)
            await self.audit_logger.log_event(
                AuditEvent(
                    event_type="error",
                    tool_name=tool_name,
                    arguments=arguments,
                    decision=False,
                    error=f"Approval provider error: {e}",
                    duration_ms=duration_ms,
                    metadata=context or {},
                )
            )
            return ToolApprovalResponse(
                approved=False,
                reason=f"Approval provider error: {e}",
            )

    def __repr__(self) -> str:
        """Return string representation of registry."""
        enabled = sum(1 for t in self._tools.values() if t.enabled)
        return (
            f"ToolRegistry(tools={len(self._tools)}, "
            f"enabled={enabled}, "
            f"approval_mode='{self.config.approval_mode}')"
        )
