"""Data models for SDK service layer.

This module defines TUI-agnostic data structures for conversation management,
streaming responses, and tool execution. These models replace LangChain-specific
types in the public API to maintain clean separation from implementation details.

Example:
    >>> token = Token(content="Hello", cost=0.0001)
    >>> attachment = Attachment(path="image.png", type="image")
    >>> stats = ConversationStats(message_count=5, total_tokens=150,
    ...                           total_cost=0.05, session_id="abc123")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.ai.tools.base import RiskLevel, ToolCategory


@dataclass
class Token:
    """Single streaming token from AI response.

    Represents an incremental piece of the AI's response during streaming.
    Includes optional cost and metadata for monitoring and analysis.

    Attributes:
        content: The text content of this token
        cost: Estimated cost in USD for this token (None if unknown)
        metadata: Additional information (tool_calls, reasoning, etc.)

    Example:
        >>> token = Token(content="Hello", cost=0.00001)
        >>> print(token.content, end="", flush=True)
        Hello
        >>> total_cost += token.cost if token.cost else 0
    """

    content: str
    cost: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return content for easy printing."""
        return self.content


@dataclass
class Attachment:
    """File attachment for messages.

    Represents a file to be sent along with a user message. Supports
    images (for multimodal models) and text files (prepended to message).

    Attributes:
        path: Absolute or relative path to the file
        type: File type - "image", "code", "document", or "data"

    Example:
        >>> image = Attachment(path="screenshot.png", type="image")
        >>> code = Attachment(path="main.py", type="code")
        >>> attachments = [image, code]
    """

    path: str
    type: str  # "image", "code", "document", "data"

    def __post_init__(self) -> None:
        """Validate attachment type."""
        valid_types = {"image", "code", "document", "data"}
        if self.type not in valid_types:
            raise ValueError(
                f"Invalid attachment type '{self.type}'. "
                f"Must be one of: {', '.join(valid_types)}"
            )


@dataclass
class ConversationStats:
    """Statistics about a conversation.

    Provides metrics for monitoring conversation history, token usage,
    and costs. Useful for analytics and cost tracking.

    Attributes:
        message_count: Total number of messages in conversation
        total_tokens: Cumulative token count across all messages
        total_cost: Total estimated cost in USD
        session_id: Unique session identifier (None if not persisted)

    Example:
        >>> stats = service.get_stats()
        >>> print(f"Messages: {stats.message_count}")
        Messages: 10
        >>> print(f"Cost: ${stats.total_cost:.4f}")
        Cost: $0.0523
    """

    message_count: int
    total_tokens: int
    total_cost: float
    session_id: str | None


@dataclass
class ToolRequest:
    """Tool execution request for approval callback.

    Encapsulates a tool call that requires approval before execution.
    Passed to the on_tool_request callback to allow the caller to
    approve or deny the execution.

    Attributes:
        id: Unique identifier for this tool call (from AI provider)
        name: Tool name to execute (e.g., "bash_execute")
        arguments: Dictionary of arguments to pass to the tool
        risk_level: Security risk level ("safe", "caution", "dangerous")

    Example:
        >>> async def approve_tool(request: ToolRequest) -> bool:
        ...     if request.risk_level == "safe":
        ...         return True  # Auto-approve safe tools
        ...     print(f"Allow {request.name}({request.arguments})? [y/n]")
        ...     return input().lower() == 'y'
        >>> async for token in service.send_message(
        ...     "List files",
        ...     on_tool_request=approve_tool
        ... ):
        ...     print(token, end="")
    """

    id: str
    name: str
    arguments: dict[str, Any]
    risk_level: str  # "safe", "caution", "dangerous", "blocked"

    def __repr__(self) -> str:
        """Human-readable representation with truncated arguments."""
        args_str = str(self.arguments)[:50]
        if len(str(self.arguments)) > 50:
            args_str += "..."
        return (
            f"ToolRequest(id={self.id!r}, name={self.name!r}, "
            f"risk={self.risk_level!r}, args={args_str})"
        )


@dataclass
class PricingInfo:
    """Pricing information for an AI model.

    Contains per-token costs in USD per million tokens (MTok).
    Supports multiple pricing tiers (standard, flex, batch, priority).

    Attributes:
        input_price: Cost per million input tokens
        output_price: Cost per million output tokens
        cache_read: Cost per million cached read tokens (optional)
        cache_write_5m: Cost per million cache write tokens, 5min TTL (optional)
        cache_write_1h: Cost per million cache write tokens, 1hr TTL (optional)
        thinking_price: Cost per million reasoning/thinking tokens (optional)
        tier: Pricing tier name ("standard", "flex", "batch", "priority")
        effective_date: When this pricing took effect (ISO date string)
        notes: Additional pricing notes (optional)

    Example:
        >>> pricing = PricingInfo(
        ...     input_price=2.50,
        ...     output_price=10.00,
        ...     cache_read=1.25,
        ...     tier="standard"
        ... )
        >>> cost_per_1k = (pricing.input_price + pricing.output_price) / 1000
        >>> print(f"~${cost_per_1k:.4f} per 1K tokens (input+output)")
    """

    input_price: float
    output_price: float
    cache_read: float | None = None
    cache_write_5m: float | None = None
    cache_write_1h: float | None = None
    thinking_price: float | None = None
    tier: str = "standard"
    effective_date: str | None = None
    notes: str | None = None


@dataclass
class ModelCapabilities:
    """Capability flags for an AI model.

    Indicates which advanced features a model supports.

    Attributes:
        supports_vision: Can process image inputs
        supports_tools: Supports function calling
        supports_reasoning: Has extended reasoning/thinking
        supports_streaming: Supports streaming responses
        supports_json_mode: Supports structured JSON output
        supports_caching: Supports prompt caching
        supports_batch: Supports batch API

    Example:
        >>> caps = ModelCapabilities(
        ...     supports_vision=True,
        ...     supports_tools=True,
        ...     supports_reasoning=True
        ... )
        >>> if caps.supports_vision and caps.supports_tools:
        ...     print("Model can process images and use tools")
    """

    supports_vision: bool = False
    supports_tools: bool = False
    supports_reasoning: bool = False
    supports_streaming: bool = False
    supports_json_mode: bool = False
    supports_caching: bool = False
    supports_batch: bool = False


@dataclass
class ThinkingContent:
    """Extracted thinking content from reasoning model responses.

    Reasoning models (DeepSeek-R1, Qwen QWQ, o1-preview) output chain-of-thought
    reasoning in XML tags like <think>...</think>. This model separates the
    thinking process from the final answer.

    Attributes:
        thinking: Content within thinking tags (reasoning process)
        answer: Content outside thinking tags (final response)
        has_thinking: Whether thinking content was detected

    Example:
        >>> detector = ThinkingDetector()
        >>> content = detector.extract(
        ...     "<think>Let me solve this...</think>The answer is 42"
        ... )
        >>> print(content.thinking)
        Let me solve this...
        >>> print(content.answer)
        The answer is 42
        >>> if content.has_thinking:
        ...     # Show thinking in collapsible UI element
    """

    thinking: str
    answer: str
    has_thinking: bool


@dataclass
class ModelInfo:
    """Information about an available AI model.

    Provides metadata about AI models for selection, display, and capability
    checking. Used by ModelService to present available models and their features.

    Attributes:
        id: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet-20241022")
        name: Human-readable display name
        provider: Provider name ("openai", "anthropic", "google", "ollama")
        context_window: Context window size as string (e.g., "128K", "1M")
        description: Brief model description
        supports_vision: Whether model supports image inputs (default: False)
        supports_tools: Whether model supports function calling (default: True)
        max_output_tokens: Maximum output tokens per request (optional)
        created: Model release date (optional, ISO date string)
        pricing: Pricing information (optional)
        capabilities: Full capability set (optional)

    Example:
        >>> model = ModelInfo(
        ...     id="gpt-4o",
        ...     name="GPT-4o",
        ...     provider="openai",
        ...     context_window="128K",
        ...     description="Fast multimodal model",
        ...     supports_vision=True
        ... )
        >>> if model.supports_vision:
        ...     print(f"{model.name} can process images")
    """

    id: str
    name: str
    provider: str
    context_window: str
    description: str
    supports_vision: bool = False
    supports_tools: bool = True
    supports_reasoning: bool = False
    max_output_tokens: int | None = None
    created: str | None = None
    pricing: PricingInfo | None = None
    capabilities: ModelCapabilities | None = None


@dataclass
class ToolFilter:
    """Fine-grained tool filtering for session-level sandboxing.

    Enables per-session tool access control for multi-tenant deployments
    where different users/sessions require different tool capabilities.
    Essential for legal/enterprise environments with strict security requirements.

    Filter rules are applied in precedence order:
    1. deny list (highest priority - blocks specific tools)
    2. allow list (whitelist - only specified tools)
    3. risk_level (filter by max risk level)
    4. categories (filter by functional category)

    Attributes:
        allow: Whitelist of allowed tool names (None = no restriction).
               Example: ["web_search", "grep_search"] for research-only session
        deny: Blacklist of blocked tool names (None = no restriction).
              Example: ["bash_execute", "file_edit"] for read-only session
        risk_level: Maximum allowed risk level (None = no restriction).
                   Example: RiskLevel.SAFE for maximum safety (read-only tools)
        categories: Allowed tool categories (None = no restriction).
                   Example: [ToolCategory.SEARCH, ToolCategory.WEB] for search-only

    Example - Legal industry (document analysis only):
        >>> from consoul.ai.tools.base import RiskLevel, ToolCategory
        >>> legal_filter = ToolFilter(
        ...     allow=["web_search", "read_url", "grep_search"],
        ...     deny=["bash_execute", "file_edit", "create_file"],
        ...     risk_level=RiskLevel.SAFE
        ... )
        >>> # Only safe search tools allowed, no bash/filesystem access

    Example - Research session (web + search, no execution):
        >>> research_filter = ToolFilter(
        ...     categories=[ToolCategory.SEARCH, ToolCategory.WEB],
        ...     deny=["bash_execute"]
        ... )

    Example - Read-only session (maximum safety):
        >>> readonly_filter = ToolFilter(
        ...     risk_level=RiskLevel.SAFE,
        ...     deny=["bash_execute", "file_edit", "create_file"]
        ... )

    Example - SDK integration with audit callback:
        >>> def audit_blocked_tool(session_id, tool_name, reason):
        ...     print(f"Blocked {tool_name}: {reason}")
        >>> service = ConversationService.from_config(
        ...     tool_filter=legal_filter,
        ...     audit_callback=audit_blocked_tool
        ... )
    """

    allow: list[str] | None = None
    deny: list[str] | None = None
    risk_level: RiskLevel | None = None
    categories: list[ToolCategory] | None = None

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        # Import here to avoid circular dependency
        from consoul.ai.tools.base import RiskLevel, ToolCategory

        # Validate risk_level
        if self.risk_level is not None and not isinstance(self.risk_level, RiskLevel):
            raise ValueError(
                f"risk_level must be RiskLevel enum, got {type(self.risk_level)}"
            )

        # Validate categories
        if self.categories is not None:
            if not isinstance(self.categories, list):
                raise ValueError("categories must be a list")
            for cat in self.categories:
                if not isinstance(cat, ToolCategory):
                    raise ValueError(
                        f"All categories must be ToolCategory enum, got {type(cat)}"
                    )

        # Validate allow/deny lists
        if self.allow is not None and not isinstance(self.allow, list):
            raise ValueError("allow must be a list of tool names")
        if self.deny is not None and not isinstance(self.deny, list):
            raise ValueError("deny must be a list of tool names")

        # Warn about conflicting configuration
        if self.allow is not None and self.deny is not None:
            # Check for overlap
            allow_set = set(self.allow)
            deny_set = set(self.deny)
            overlap = allow_set & deny_set
            if overlap:
                import warnings

                warnings.warn(
                    f"ToolFilter has overlapping allow/deny lists: {overlap}. "
                    "deny list takes precedence.",
                    UserWarning,
                    stacklevel=2,
                )

    def is_tool_allowed(
        self,
        tool_name: str,
        tool_risk: RiskLevel,
        tool_categories: list[ToolCategory] | None = None,
    ) -> tuple[bool, str | None]:
        """Check if a tool is allowed by this filter.

        Args:
            tool_name: Name of the tool to check
            tool_risk: Risk level of the tool
            tool_categories: Optional categories for the tool

        Returns:
            Tuple of (is_allowed, reason). If not allowed, reason explains why.

        Example:
            >>> filter = ToolFilter(deny=["bash_execute"], risk_level=RiskLevel.SAFE)
            >>> allowed, reason = filter.is_tool_allowed("bash_execute", RiskLevel.CAUTION)
            >>> assert not allowed
            >>> assert "denied by filter" in reason
        """
        # Import here to avoid circular dependency
        from consoul.ai.tools.base import RiskLevel

        # 1. Check deny list (highest priority)
        if self.deny and tool_name in self.deny:
            return False, f"Tool '{tool_name}' is explicitly denied by filter"

        # 2. Check allow list (whitelist)
        if self.allow is not None and tool_name not in self.allow:
            return False, f"Tool '{tool_name}' is not in allow list"

        # 3. Check risk level
        if self.risk_level is not None:
            # Get risk level priority (safe=0, caution=1, dangerous=2, blocked=3)
            risk_priority = {
                RiskLevel.SAFE: 0,
                RiskLevel.CAUTION: 1,
                RiskLevel.DANGEROUS: 2,
                RiskLevel.BLOCKED: 3,
            }
            max_priority = risk_priority.get(self.risk_level, 0)
            tool_priority = risk_priority.get(tool_risk, 3)

            if tool_priority > max_priority:
                return (
                    False,
                    f"Tool '{tool_name}' risk level {tool_risk.value} exceeds maximum {self.risk_level.value}",
                )

        # 4. Check categories
        if self.categories is not None:
            # If category filter is active, tool MUST have categories
            if not tool_categories:
                return (
                    False,
                    f"Tool '{tool_name}' has no category metadata (required when using category filter)",
                )

            # Tool must have at least one allowed category
            if not any(cat in self.categories for cat in tool_categories):
                allowed_cats = ", ".join(c.value for c in self.categories)
                return (
                    False,
                    f"Tool '{tool_name}' categories not in allowed list: {allowed_cats}",
                )

        return True, None


@dataclass
class SessionState:
    """Serializable session state for HTTP endpoints and multi-user backends.

    Contains all information needed to persist and restore a Consoul session
    across HTTP requests without using pickle (which has RCE vulnerabilities).
    Only stores JSON-serializable data: conversation history, config, and metadata.

    Attributes:
        session_id: Unique session identifier
        model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet-20241022")
        temperature: Temperature setting (0.0 to 2.0)
        messages: Conversation history as LangChain message dicts
        created_at: Unix timestamp when session was created
        updated_at: Unix timestamp when session was last updated
        config: Additional configuration (tools, system_prompt, max_tokens, etc.)

    Example - Save session state:
        >>> from consoul.sdk import create_session, save_session_state
        >>> console = create_session(session_id="user123", model="gpt-4o")
        >>> console.chat("Hello!")
        >>> state = save_session_state(console)
        >>> # Store state.to_dict() in Redis/database/file

    Example - Restore session state:
        >>> from consoul.sdk import restore_session
        >>> state_dict = load_from_storage("user123")
        >>> state = SessionState.from_dict(state_dict)
        >>> console = restore_session(state)
        >>> console.chat("Continue conversation")

    Security Notes:
        - Only JSON-serializable data (no Consoul objects, no pickle)
        - No executable code in messages or config
        - Validate all data when deserializing
        - Use secure session_id (UUID, JWT subject, not sequential)
    """

    session_id: str
    model: str
    temperature: float
    messages: list[dict[str, Any]]
    created_at: float
    updated_at: float
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert session state to JSON-serializable dictionary.

        Returns:
            Dictionary with all session state fields

        Example:
            >>> state = SessionState(
            ...     session_id="user123",
            ...     model="gpt-4o",
            ...     temperature=0.7,
            ...     messages=[{"role": "user", "content": "Hi"}],
            ...     created_at=time.time(),
            ...     updated_at=time.time()
            ... )
            >>> state_dict = state.to_dict()
            >>> json.dumps(state_dict)  # JSON-serializable
        """
        return {
            "session_id": self.session_id,
            "model": self.model,
            "temperature": self.temperature,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionState:
        """Create session state from dictionary.

        Args:
            data: Dictionary with session state fields

        Returns:
            SessionState instance

        Raises:
            ValueError: If required fields are missing or invalid

        Example:
            >>> state_dict = {
            ...     "session_id": "user123",
            ...     "model": "gpt-4o",
            ...     "temperature": 0.7,
            ...     "messages": [],
            ...     "created_at": 1704067200.0,
            ...     "updated_at": 1704067200.0
            ... }
            >>> state = SessionState.from_dict(state_dict)
        """
        required_fields = [
            "session_id",
            "model",
            "temperature",
            "messages",
            "created_at",
            "updated_at",
        ]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")

        return cls(
            session_id=data["session_id"],
            model=data["model"],
            temperature=data["temperature"],
            messages=data["messages"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            config=data.get("config", {}),
        )
