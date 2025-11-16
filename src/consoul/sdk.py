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

from typing import Any

from consoul.ai import ConversationHistory, get_chat_model
from consoul.ai.tools import (
    RiskLevel,
    ToolRegistry,
    append_to_file,
    bash_execute,
    code_search,
    create_file,
    delete_file,
    edit_file_lines,
    edit_file_search_replace,
    find_references,
    grep_search,
)
from consoul.ai.tools.permissions import PermissionPolicy
from consoul.ai.tools.providers import CliApprovalProvider
from consoul.config import load_config
from consoul.config.models import ConsoulConfig, ToolConfig


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
        tools: bool = True,
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
            tools: Enable tool calling with CLI approval (default: False)
            temperature: Override temperature (0.0-2.0)
            system_prompt: Override system prompt
            persist: Save conversation history (default: True)
            api_key: Override API key (falls back to environment)
            discover_tools: Auto-discover available tools (default: False)

        Raises:
            ValueError: If profile not found or invalid parameters
            MissingAPIKeyError: If no API key found for provider

        Examples:
            >>> console = Consoul()  # Use defaults
            >>> console = Consoul(model="gpt-4o", temperature=0.7)
            >>> console = Consoul(profile="code-review", tools=True)
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
        self.tools_enabled = tools
        self.discover_tools = discover_tools
        self.registry: ToolRegistry | None = None
        if tools:
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

    def _setup_tools(self) -> None:
        """Setup tool calling with CLI approval."""
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

        # Register bash tool
        self.registry.register(
            tool=bash_execute,
            risk_level=RiskLevel.CAUTION,
        )

        # Register grep_search tool
        self.registry.register(
            tool=grep_search,
            risk_level=RiskLevel.SAFE,
        )

        # Register code_search tool
        self.registry.register(
            tool=code_search,
            risk_level=RiskLevel.SAFE,
        )

        # Register find_references tool
        self.registry.register(
            tool=find_references,
            risk_level=RiskLevel.SAFE,
        )

        # Register file edit tools
        self.registry.register(
            tool=create_file,
            risk_level=RiskLevel.CAUTION,
        )

        self.registry.register(
            tool=edit_file_lines,
            risk_level=RiskLevel.CAUTION,
        )

        self.registry.register(
            tool=edit_file_search_replace,
            risk_level=RiskLevel.CAUTION,
        )

        self.registry.register(
            tool=append_to_file,
            risk_level=RiskLevel.CAUTION,
        )

        self.registry.register(
            tool=delete_file,
            risk_level=RiskLevel.DANGEROUS,
        )

        # Bind tools to model
        self.model = self.registry.bind_to_model(self.model)

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

        # Add user message synchronously (persistence handled later if enabled)
        from langchain_core.messages import HumanMessage

        # Just add to memory, no persistence in sync SDK
        user_message = HumanMessage(content=message)
        self.history.messages.append(user_message)

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
        """Get estimated cost of last request.

        Returns:
            Dictionary with input_tokens, output_tokens, and estimated cost

        Examples:
            >>> console.chat("Hello")
            >>> console.last_cost
            {'input_tokens': 10, 'output_tokens': 15, 'total_cost': 0.00025}

        Note:
            Cost estimates are approximate and based on standard pricing.
            Actual costs may vary.
        """
        if not self._last_request:
            return {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}

        # Calculate token delta
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
        total_cost = (input_tokens * cost_per_input) + (output_tokens * cost_per_output)

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": tokens_used,
            "estimated_cost": round(total_cost, 6),
            "model": self.model_name,
        }
