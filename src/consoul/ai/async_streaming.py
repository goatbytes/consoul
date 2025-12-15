"""Async streaming primitives for AI model responses.

This module provides async-native streaming utilities for integrating AI responses
into web backends (WebSocket, SSE, etc.) without CLI/console dependencies.

Key differences from streaming.py:
- Async generators instead of synchronous streaming
- Event-based protocol (yields StreamEvent objects)
- No Rich console output - pure data streaming
- Suitable for WebSocket/SSE endpoints

Example:
    >>> from consoul.ai import get_chat_model
    >>> from consoul.ai.async_streaming import async_stream_events
    >>>
    >>> model = get_chat_model("gpt-4o", api_key="...")
    >>> messages = [{"role": "user", "content": "Hello!"}]
    >>>
    >>> async for event in async_stream_events(model, messages):
    ...     if event.type == "token":
    ...         print(event.data["text"], end="")
    ...     elif event.type == "tool_call":
    ...         print(f"\\nTool: {event.data['name']}")
    ...     elif event.type == "done":
    ...         print(f"\\nComplete: {event.data['message'].content}")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from consoul.ai.exceptions import StreamingError

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage, BaseMessage


class StreamEvent(BaseModel):
    """Event emitted during async streaming.

    Attributes:
        type: Event type - "token", "tool_call", or "done"
        data: Event payload specific to the event type

    Event Types:
        - token: Individual text token from the model
          data: {"text": str}
        - tool_call: Complete tool call after accumulation
          data: {"name": str, "args": dict, "id": str}
        - done: Final event with complete AIMessage
          data: {"message": AIMessage, "text": str}
    """

    type: Literal["token", "tool_call", "done"] = Field(
        description="Type of streaming event"
    )
    data: dict[str, Any] = Field(description="Event-specific payload data")


async def async_stream_events(
    model: BaseChatModel,
    messages: list[BaseMessage],
) -> AsyncGenerator[StreamEvent, None]:
    """Stream AI response as async events without console output.

    Yields StreamEvent objects as the model generates tokens and tool calls.
    Suitable for WebSocket/SSE implementations in web backends.

    Args:
        model: LangChain chat model with .astream() support
        messages: Conversation messages as LangChain BaseMessage objects

    Yields:
        StreamEvent objects with types:
        - "token": Each text token as it arrives
        - "tool_call": Complete tool call after chunk accumulation
        - "done": Final event with complete AIMessage

    Raises:
        StreamingError: If streaming fails or is interrupted

    Example:
        >>> async for event in async_stream_events(model, messages):
        ...     match event.type:
        ...         case "token":
        ...             await websocket.send_json({"token": event.data["text"]})
        ...         case "tool_call":
        ...             await websocket.send_json({"tool_call": event.data})
        ...         case "done":
        ...             await websocket.send_json({"complete": True})

    Note:
        This function uses the same chunk reconstruction logic as stream_response()
        from streaming.py, ensuring consistent behavior between CLI and web backends.
    """
    # Import here to avoid circular dependency
    from consoul.ai.streaming import _reconstruct_ai_message

    collected_chunks: list[AIMessage] = []
    collected_tokens: list[str] = []

    try:
        async for chunk in model.astream(messages):
            # Collect all chunks (even empty ones) for tool_calls reconstruction
            collected_chunks.append(chunk)

            # Yield token events for non-empty content
            if chunk.content:
                token = (
                    chunk.content
                    if isinstance(chunk.content, str)
                    else str(chunk.content)
                )
                collected_tokens.append(token)

                yield StreamEvent(type="token", data={"text": token})

        # Reconstruct final AIMessage with tool_calls
        final_message = _reconstruct_ai_message(collected_chunks)

        # Yield tool_call events for each tool call
        if final_message.tool_calls:
            for tool_call in final_message.tool_calls:
                yield StreamEvent(
                    type="tool_call",
                    data={
                        "name": tool_call.get("name", ""),
                        "args": tool_call.get("args", {}),
                        "id": tool_call.get("id"),
                    },
                )

        # Yield final completion event
        yield StreamEvent(
            type="done",
            data={
                "message": final_message,
                "text": "".join(collected_tokens),
            },
        )

    except KeyboardInterrupt:
        # Graceful handling of Ctrl+C - preserve partial response
        partial_response = "".join(collected_tokens)
        raise StreamingError(
            "Streaming interrupted by user", partial_response=partial_response
        ) from KeyboardInterrupt()

    except Exception as e:
        # Preserve partial response for debugging/recovery
        partial_response = "".join(collected_tokens)
        raise StreamingError(
            f"Streaming failed: {e}", partial_response=partial_response
        ) from e
