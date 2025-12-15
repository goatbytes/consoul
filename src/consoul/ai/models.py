"""Data models for AI streaming responses.

This module provides Pydantic models for streaming chunks, decoupled
from UI/presentation concerns to enable headless SDK usage.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StreamChunk(BaseModel):
    """Raw streaming chunk from AI model without UI dependencies.

    Represents a single chunk of streamed content with associated metadata.
    Used for headless streaming where presentation is handled separately.

    Attributes:
        content: Text content of the chunk
        tokens: Estimated token count for this chunk (0 if not calculated)
        cost: Estimated cost for this chunk in USD (0.0 if not calculated)
        metadata: Additional metadata (provider-specific, timing, etc.)

    Example:
        >>> chunk = StreamChunk(content="Hello", tokens=1, cost=0.00001)
        >>> print(chunk.content)
        Hello
        >>> chunk.tokens
        1
    """

    model_config = ConfigDict(
        frozen=False,  # Allow mutation for cost/token updates
        extra="forbid",  # Reject unknown fields
    )

    content: str = Field(description="Text content of the streaming chunk")
    tokens: int = Field(default=0, description="Estimated token count")
    cost: float = Field(default=0.0, description="Estimated cost in USD")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional chunk metadata"
    )
