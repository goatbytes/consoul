"""High-level SDK for easy Consoul integration.

This module provides a simple, intuitive API for adding AI capabilities
to Python applications with minimal code.

Examples:
    Minimal usage (5 lines):
        >>> from consoul import Consoul
        >>> console = Consoul()
        >>> console.chat("What is 2+2?")
        '4'

    With customization:
        >>> console = Consoul(model="gpt-4o", tools=True, temperature=0.7)
        >>> response = console.ask("Hello", show_tokens=True)
        >>> print(f"Tokens: {response.tokens}")
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from consoul.ai import ConversationHistory, get_chat_model
from consoul.ai.tools import RiskLevel, ToolCategory, ToolRegistry
from consoul.ai.tools.catalog import (
    get_all_category_names,
    get_all_tool_names,
    get_tool_by_name,
    get_tools_by_category,
    get_tools_by_risk_level,
    validate_category_name,
)
from consoul.ai.tools.discovery import discover_tools_from_directory
from consoul.ai.tools.permissions import PermissionPolicy
from consoul.ai.tools.providers import CliApprovalProvider
from consoul.config import load_config
from consoul.config.models import ConsoulConfig, ToolConfig

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


class ConsoulResponse:
    """Response from Consoul chat/ask methods.

    Attributes:
        content: The AI's response text
        tokens: Number of tokens used (if requested)
        model: Model name that generated the response

    Examples:
        >>> response = console.ask("Hello", show_tokens=True)
        >>> print(response.content)
        >>> print(f"Tokens: {response.tokens}")
    """

    def __init__(self, content: str, tokens: int = 0, model: str = ""):
        """Initialize response.

        Args:
            content: Response text
            tokens: Token count
            model: Model name
        """
        self.content = content
        self.tokens = tokens
        self.model = model

    def __str__(self) -> str:
        """Return content as string for easy printing."""
        return self.content

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"ConsoulResponse(content={self.content[:50]!r}..., tokens={self.tokens}, model={self.model!r})"


class Consoul:
    """High-level Consoul SDK interface.

    The easiest way to add AI chat to your Python application.

    Examples:
        Basic chat:
            >>> console = Consoul()
            >>> console.chat("Hello!")
            'Hi! How can I help you?'

        With tools:
            >>> console = Consoul(tools=True)
            >>> console.chat("List files")

        Custom model:
            >>> console = Consoul(model="gpt-4o")
            >>> response = console.ask("Explain", show_tokens=True)
            >>> print(f"Tokens: {response.tokens}")

        Introspection:
            >>> console.settings
            {'model': 'claude-3-5-sonnet-20241022', 'profile': 'default', ...}
            >>> console.last_cost
            {'input_tokens': 10, 'output_tokens': 15, 'total_cost': 0.00025}
    """

    def __init__(
        self,
        model: str | None = None,
        profile: str = "default",
        tools: bool | str | list[str | BaseTool] | None = True,
        temperature: float | None = None,
        system_prompt: str | None = None,
        persist: bool = True,
        api_key: str | None = None,
        discover_tools: bool = False,
    ):
        """Initialize Consoul SDK.

        Args:
            model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet").
                   Auto-detects provider. Defaults to profile's model.
            profile: Profile name to use (default: "default")
            tools: Tool specification. Supports multiple formats:
                   - True: Enable all built-in tools (default)
                   - False/None: Disable all tools (chat-only mode)
                   - "safe"/"caution"/"dangerous": Risk level filtering
                   - "search"/"file-edit"/"web"/"execute": Category filtering
                   - ["bash", "grep"]: Specific tools by name
                   - ["search", "web"]: Multiple categories
                   - ["search", "bash"]: Mix categories and tools
                   - [custom_tool, "bash"]: Mix custom and built-in tools

                   Security guidelines:
                   - SAFE: Read-only operations (grep, code_search, web_search)
                   - CAUTION: File operations and command execution (requires oversight)
                   - Start with tools="safe" for untrusted AI interactions
                   - Use principle of least privilege (only grant needed tools)
                   - Always use version control (git) when enabling file operations

            temperature: Override temperature (0.0-2.0)
            system_prompt: Override system prompt
            persist: Save conversation history (default: True)
            api_key: Override API key (falls back to environment)
            discover_tools: Auto-discover tools from .consoul/tools/ (default: False)
                            Discovered tools default to CAUTION risk level.

        Raises:
            ValueError: If profile not found or invalid parameters
            MissingAPIKeyError: If no API key found for provider

        Examples:
            Basic usage:
                >>> console = Consoul()  # All tools enabled
                >>> console = Consoul(model="gpt-4o", temperature=0.7)

            Tool specification:
                >>> # Disable tools
                >>> console = Consoul(tools=False)

                >>> # Only safe read-only tools
                >>> console = Consoul(tools="safe")

                >>> # Specific tools by name
                >>> console = Consoul(tools=["bash", "grep", "code_search"])

                >>> # Custom tool + built-in
                >>> from langchain_core.tools import tool
                >>> @tool
                ... def my_tool(query: str) -> str:
                ...     return "result"
                >>> console = Consoul(tools=[my_tool, "bash"])

            Category-based specification:
                >>> # All search tools
                >>> console = Consoul(tools="search")

                >>> # All file editing tools
                >>> console = Consoul(tools="file-edit")

                >>> # Multiple categories
                >>> console = Consoul(tools=["search", "web"])

                >>> # Mix categories and specific tools
                >>> console = Consoul(tools=["search", "bash"])

            Tool discovery:
                >>> # Auto-discover tools from .consoul/tools/
                >>> console = Consoul(discover_tools=True)

                >>> # Combine with specific tools
                >>> console = Consoul(tools=["bash", "grep"], discover_tools=True)

                >>> # Only discovered tools (no built-in)
                >>> console = Consoul(tools=False, discover_tools=True)

        Available tool categories:
            search, file-edit, web, execute

        Available tool names:
            bash, grep, code_search, find_references, create_file,
            edit_lines, edit_replace, append_file, delete_file,
            read_url, web_search

        Tool discovery:
            When discover_tools=True, Consoul will scan .consoul/tools/ for
            custom tools. Create a .consoul/tools/ directory in your project
            and add Python files with @tool decorated functions:

                .consoul/tools/my_tool.py:
                    from langchain_core.tools import tool

                    @tool
                    def my_custom_tool(query: str) -> str:
                        '''My custom tool description.'''
                        return process(query)

            All discovered tools default to RiskLevel.CAUTION for safety.
        """
        # Validate temperature
        if temperature is not None and not 0.0 <= temperature <= 2.0:
            raise ValueError(
                f"Temperature must be between 0.0 and 2.0, got {temperature}"
            )

        # Load configuration
        self.config: ConsoulConfig = load_config()

        # Get profile
        if profile not in self.config.profiles:
            from consoul.config.profiles import get_builtin_profiles

            builtin = get_builtin_profiles()
            if profile in builtin:
                # Convert builtin profile dict to ProfileConfig
                from consoul.config.models import ProfileConfig

                profile_dict = builtin[profile]
                self.profile = ProfileConfig(**profile_dict)
            else:
                available = list(self.config.profiles.keys()) + list(builtin.keys())
                raise ValueError(
                    f"Profile '{profile}' not found. "
                    f"Available profiles: {', '.join(available)}"
                )
        else:
            self.profile = self.config.profiles[profile]

        # Override system prompt if specified
        if system_prompt is not None:
            self.profile.system_prompt = system_prompt

        # Initialize model
        if model:
            # Use specific model
            from pydantic import SecretStr

            api_key_secret = SecretStr(api_key) if api_key else None
            self.model = get_chat_model(
                model, config=self.config, api_key=api_key_secret
            )
            self.model_name = model
        else:
            # Use config's current model
            from pydantic import SecretStr

            api_key_secret = SecretStr(api_key) if api_key else None
            self.model = get_chat_model(
                self.config.current_model, config=self.config, api_key=api_key_secret
            )
            self.model_name = self.config.current_model

        # Store temperature override
        self.temperature = temperature

        # Initialize conversation history
        self.history = ConversationHistory(
            model_name=self.model_name,
            model=self.model,
            persist=persist,
            **self._get_conversation_kwargs(),
        )

        # Add system prompt
        if self.profile.system_prompt:
            self.history.add_system_message(self.profile.system_prompt)

        # Initialize tools if requested
        self.tools_spec = tools
        self.discover_tools = discover_tools
        self.tools_enabled = (
            False  # Will be set to True if tools are actually registered
        )
        self.registry: ToolRegistry | None = None
        if (tools is not False and tools is not None) or discover_tools:
            self._setup_tools()

        # Track last request for introspection
        self._last_request: dict[str, Any] | None = None
        self._last_response: Any | None = None

    def _get_conversation_kwargs(self) -> dict[str, Any]:
        """Get ConversationHistory kwargs from profile.

        Returns:
            Dictionary of kwargs for ConversationHistory
        """
        conv = self.profile.conversation
        kwargs: dict[str, Any] = {
            "db_path": conv.db_path,
            "summarize": conv.summarize,
            "summarize_threshold": conv.summarize_threshold,
            "keep_recent": conv.keep_recent,
        }

        # Handle summary_model
        if conv.summary_model:
            kwargs["summary_model"] = get_chat_model(
                conv.summary_model, config=self.config
            )

        return kwargs

    def _validate_and_resolve_tools(
        self,
    ) -> list[tuple[BaseTool, RiskLevel, list[ToolCategory]]]:
        """Validate and resolve tool specification to list of (tool, risk_level, categories).

        Returns:
            List of (tool, risk_level, categories) tuples to register

        Raises:
            ValueError: If tool specification is invalid
        """
        tools_spec = self.tools_spec

        # Handle boolean values (backward compatibility)
        if tools_spec is True:
            # All tools (current behavior)
            return list(get_tools_by_risk_level(RiskLevel.DANGEROUS))

        if tools_spec is False or tools_spec is None:
            # No tools
            return []

        # Handle strings (risk level, category, or tool name)
        if isinstance(tools_spec, str):
            risk_levels = {"safe", "caution", "dangerous"}

            # Check if it's a risk level
            if tools_spec.lower() in risk_levels:
                return list(get_tools_by_risk_level(tools_spec.lower()))

            # Check if it's a category
            if validate_category_name(tools_spec):
                return list(get_tools_by_category(tools_spec))

            # Check if it's a tool name
            result = get_tool_by_name(tools_spec)
            if result is None:
                available_categories = get_all_category_names()
                available_tools = get_all_tool_names()
                raise ValueError(
                    f"Unknown tool or category '{tools_spec}'. "
                    f"Categories: {', '.join(available_categories)}. "
                    f"Tools: {', '.join(available_tools)}"
                )
            return [result]

        # Handle list of tools and/or categories
        if isinstance(tools_spec, list):
            if not tools_spec:
                return []  # Empty list = no tools

            resolved_tools: list[tuple[BaseTool, RiskLevel, list[ToolCategory]]] = []

            for tool_spec in tools_spec:
                if isinstance(tool_spec, str):
                    # Check if it's a category first
                    if validate_category_name(tool_spec):
                        # Add all tools from this category
                        category_tools = get_tools_by_category(tool_spec)
                        resolved_tools.extend(category_tools)
                    else:
                        # Tool name lookup
                        result = get_tool_by_name(tool_spec)
                        if result is None:
                            available_categories = get_all_category_names()
                            available_tools = get_all_tool_names()
                            raise ValueError(
                                f"Unknown tool or category '{tool_spec}'. "
                                f"Categories: {', '.join(available_categories)}. "
                                f"Tools: {', '.join(available_tools)}"
                            )
                        resolved_tools.append(result)
                elif hasattr(tool_spec, "name") and hasattr(tool_spec, "run"):
                    # Check if it's a BaseTool instance (custom tool)
                    # Assume custom tools are CAUTION level by default
                    resolved_tools.append((tool_spec, RiskLevel.CAUTION, []))
                else:
                    raise ValueError(
                        f"Invalid tool specification: {tool_spec}. "
                        "Must be a tool name (str) or BaseTool instance."
                    )

            return resolved_tools

        # Invalid type
        raise ValueError(
            f"Invalid tools parameter type: {type(tools_spec)}. "
            "Must be bool, str, list, or None."
        )

    def _setup_tools(self) -> None:
        """Setup tool calling with CLI approval."""
        # Validate and resolve tool specification
        tools_to_register = self._validate_and_resolve_tools()

        # Discover custom tools if enabled
        if self.discover_tools:
            tools_dir = Path.cwd() / ".consoul" / "tools"
            discovered_tools = discover_tools_from_directory(tools_dir, recursive=True)
            # Convert (tool, risk) to (tool, risk, []) for discovered tools
            tools_to_register.extend(
                [(tool, risk, []) for tool, risk in discovered_tools]
            )

        # Deduplicate tools by name (last occurrence wins)
        # This allows mixing categories with specific tools (e.g., tools=["search", "grep"])
        # without raising ToolValidationError for duplicates
        seen_names: dict[str, tuple[BaseTool, RiskLevel, list[ToolCategory]]] = {}
        for tool, risk_level, categories in tools_to_register:
            seen_names[tool.name] = (tool, risk_level, categories)
        tools_to_register = list(seen_names.values())

        if not tools_to_register:
            # No tools to register
            self.tools_enabled = False
            return

        # Create tool registry
        tool_config = ToolConfig(
            enabled=True,
            permission_policy=PermissionPolicy.BALANCED,
            audit_logging=True,
        )

        approval_provider = CliApprovalProvider(show_arguments=True)

        self.registry = ToolRegistry(
            config=tool_config,
            approval_provider=approval_provider,
        )

        # Register all resolved tools
        for tool, risk_level, _categories in tools_to_register:
            self.registry.register(
                tool=tool,
                risk_level=risk_level,
            )

        # Bind tools to model
        self.model = self.registry.bind_to_model(self.model)

        # Mark tools as enabled
        self.tools_enabled = True

    def _track_request(self, message: str) -> None:
        """Track last request for introspection.

        Args:
            message: User message sent
        """
        self._last_request = {
            "message": message,
            "model": self.model_name,
            "messages_count": len(self.history),
            "tokens_before": self.history.count_tokens(),
        }

    def _track_response(self, response: Any) -> None:
        """Track last response for introspection.

        Args:
            response: Model response
        """
        self._last_response = response

    def chat(self, message: str) -> str:
        """Send a message and get a response.

        This is a stateful method - conversation history is maintained
        across multiple calls.

        Args:
            message: Your message to the AI

        Returns:
            AI's response as a string

        Examples:
            >>> console.chat("What is 2+2?")
            '4'
            >>> console.chat("What about 3+3?")  # Remembers context
            '6'
        """
        self._track_request(message)

        # Add user message (synchronous version for SDK)
        self.history.add_user_message(message)

        # Get response (streaming handled internally)
        messages = self.history.get_trimmed_messages(reserve_tokens=1000)
        response = self.model.invoke(messages)

        self._track_response(response)

        # Handle tool calls if present
        if self.tools_enabled and self._has_tool_calls(response):
            response = self._execute_tool_loop(response)

        # Extract content - handle both string and list responses
        content_str: str
        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, list):
                # Join list items into string
                content_str = "".join(str(item) for item in content)
            else:
                content_str = str(content)
        else:
            content_str = str(response)

        self.history.add_assistant_message(content_str)
        return content_str

    def _has_tool_calls(self, response: Any) -> bool:
        """Check if response has tool calls.

        Args:
            response: Model response

        Returns:
            True if response has tool calls
        """
        return hasattr(response, "tool_calls") and bool(response.tool_calls)

    def _execute_tool_loop(self, response: Any) -> Any:
        """Execute tool calls and get final response.

        Args:
            response: Initial response with tool calls

        Returns:
            Final response after tool execution
        """
        from langchain_core.messages import ToolMessage

        max_iterations = 5  # Prevent infinite loops
        iteration = 0

        while self._has_tool_calls(response) and iteration < max_iterations:
            iteration += 1

            # Add AI message with tool calls to history
            self.history.messages.append(response)

            # Parse and execute tool calls
            from consoul.ai.tools.parser import parse_tool_calls

            parsed_calls = parse_tool_calls(response)

            # Execute each tool call and collect results
            tool_messages = []
            for tool_call in parsed_calls:
                try:
                    # Get the tool from the registry
                    if self.registry:
                        tool_metadata = self.registry.get_tool(tool_call.name)
                        # Invoke the tool directly
                        result = tool_metadata.tool.invoke(tool_call.arguments)
                        tool_messages.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call.id,
                            )
                        )
                except Exception as e:
                    # Add error message
                    tool_messages.append(
                        ToolMessage(
                            content=f"Error executing {tool_call.name}: {e}",
                            tool_call_id=tool_call.id,
                        )
                    )

            # Add tool results to history
            self.history.messages.extend(tool_messages)

            # Get next response from model with tool results
            messages = self.history.get_trimmed_messages(reserve_tokens=1000)
            response = self.model.invoke(messages)

            # Track the latest response for accurate token usage
            self._track_response(response)

        return response

    def ask(self, message: str, show_tokens: bool = False) -> ConsoulResponse:
        """Send a message and get a rich response with metadata.

        Args:
            message: Your message
            show_tokens: Include token count in response

        Returns:
            ConsoulResponse with content, tokens, and model info

        Examples:
            >>> response = console.ask("Hello", show_tokens=True)
            >>> print(response.content)
            >>> print(f"Tokens: {response.tokens}")
        """
        content = self.chat(message)

        tokens = 0
        if show_tokens:
            tokens = self.history.count_tokens()

        return ConsoulResponse(
            content=content,
            tokens=tokens,
            model=self.model_name,
        )

    def clear(self) -> None:
        """Clear conversation history and start fresh.

        The system prompt is preserved.

        Examples:
            >>> console.chat("Hello")
            >>> console.chat("Remember me?")  # AI remembers
            >>> console.clear()
            >>> console.chat("Remember me?")  # AI doesn't remember
        """
        self.history.clear()
        if self.profile.system_prompt:
            self.history.add_system_message(self.profile.system_prompt)

    @property
    def settings(self) -> dict[str, Any]:
        """Get current configuration settings.

        Returns:
            Dictionary with model, profile, tools, and other settings

        Examples:
            >>> console.settings
            {'model': 'claude-3-5-sonnet-20241022', 'profile': 'default', ...}
        """
        return {
            "model": self.model_name,
            "profile": self.profile.name,
            "tools_enabled": self.tools_enabled,
            "discover_tools": self.discover_tools,
            "persist": self.history.persist
            if hasattr(self.history, "persist")
            else True,
            "temperature": self.temperature,
            "system_prompt": self.profile.system_prompt,
            "conversation_length": len(self.history),
            "total_tokens": self.history.count_tokens(),
        }

    @property
    def last_request(self) -> dict[str, Any] | None:
        """Get details about the last API request.

        Returns:
            Dictionary with message, model, token count, etc.
            None if no requests made yet.

        Examples:
            >>> console.chat("Hello")
            >>> console.last_request
            {'message': 'Hello', 'model': 'claude-3-5-sonnet-20241022', ...}
        """
        return self._last_request

    @property
    def last_cost(self) -> dict[str, Any]:
        """Get token usage and estimated cost of last request.

        Returns:
            Dictionary with input_tokens, output_tokens, total_tokens, and estimated cost

        Examples:
            >>> console.chat("Hello")
            >>> console.last_cost
            {'input_tokens': 87, 'output_tokens': 12, 'total_tokens': 99, ...}

        Note:
            Token counts are accurate when available from the model provider.
            Falls back to conversation history token counting if unavailable.
            Cost estimates use hard-coded pricing and may not reflect actual costs.
        """
        if not self._last_request:
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
                "model": self.model_name,
                "source": "none",
            }

        # Try to get actual usage metadata from response
        if self._last_response and hasattr(self._last_response, "usage_metadata"):
            metadata = self._last_response.usage_metadata
            if metadata:
                input_tokens = metadata.get("input_tokens", 0)
                output_tokens = metadata.get("output_tokens", 0)
                total_tokens = metadata.get(
                    "total_tokens", input_tokens + output_tokens
                )

                # Cost calculation (still uses hard-coded pricing - SOUL-185 will fix this)
                cost_per_input = 0.000003  # $3 per 1M tokens
                cost_per_output = 0.000015  # $15 per 1M tokens
                estimated_cost = (input_tokens * cost_per_input) + (
                    output_tokens * cost_per_output
                )

                return {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost": round(estimated_cost, 6),
                    "model": self.model_name,
                    "source": "usage_metadata",  # Indicates accurate token counts
                }

        # Fallback: Calculate from conversation history (approximation)
        tokens_before = self._last_request.get("tokens_before", 0)
        tokens_after = self.history.count_tokens()
        tokens_used = tokens_after - tokens_before

        # Rough estimate: assume 60/40 split input/output
        input_tokens = int(tokens_used * 0.6)
        output_tokens = int(tokens_used * 0.4)

        # Rough cost estimate (varies by model)
        # Using approximate Claude pricing: $3/$15 per M tokens
        cost_per_input = 0.000003  # $3 per 1M tokens
        cost_per_output = 0.000015  # $15 per 1M tokens
        estimated_cost = (input_tokens * cost_per_input) + (
            output_tokens * cost_per_output
        )

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": tokens_used,
            "estimated_cost": round(estimated_cost, 6),
            "model": self.model_name,
            "source": "approximation",  # Indicates fallback was used
        }
