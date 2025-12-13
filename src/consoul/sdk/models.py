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
from typing import Any


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
    max_output_tokens: int | None = None
    created: str | None = None
    pricing: PricingInfo | None = None
    capabilities: ModelCapabilities | None = None
