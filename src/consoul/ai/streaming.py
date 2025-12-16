"""Streaming response handling for AI chat models.

This module provides utilities for streaming responses from AI models
token-by-token. Core streaming logic is decoupled from UI/presentation
to enable headless SDK usage.

Recommended Usage:
    For new code, use stream_chunks() (headless) or async_stream_events() (async):
    >>> from consoul.ai import stream_chunks
    >>> for chunk in stream_chunks(model, messages):
    ...     print(chunk.content, end="")

    For CLI/TUI with Rich formatting:
    >>> from consoul.ai import stream_chunks
    >>> from consoul.presentation import display_stream_with_rich
    >>> chunks = stream_chunks(model, messages)
    >>> response = display_stream_with_rich(chunks)

Legacy Usage (Deprecated):
    >>> from consoul.ai import stream_response  # Deprecated
    >>> response_text, ai_message = stream_response(model, messages)
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from consoul.ai.exceptions import StreamingError
from consoul.ai.models import StreamChunk

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage, BaseMessage


def _reconstruct_ai_message(chunks: list[AIMessage]) -> AIMessage:
    """Reconstruct final AIMessage from streamed chunks.

    Aggregates content and tool_calls from all chunks to create the complete
    AIMessage that the model would have returned via invoke().

    Args:
        chunks: List of AIMessage chunks from model.stream()

    Returns:
        Complete AIMessage with aggregated content and tool_calls

    Note:
        Tool calls are streamed incrementally across chunks:
        - Early chunks have name, id, and args='' (empty string)
        - Later chunks have incremental args updates like '{"', 'command', '":"', 'ls', '"}'
        - This function concatenates args strings by index, then parses final JSON
    """
    from langchain_core.messages import AIMessage

    if not chunks:
        return AIMessage(content="")

    # Accumulate content
    content_parts: list[str] = []
    for chunk in chunks:
        if chunk.content:
            token = (
                chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            )
            content_parts.append(token)

    # Accumulate tool_call_chunks from all chunks
    tool_calls_by_index: dict[int, dict[str, Any]] = {}

    for chunk in chunks:
        # Use tool_call_chunks (raw streaming data), not tool_calls (pre-parsed)
        if not hasattr(chunk, "tool_call_chunks") or not chunk.tool_call_chunks:
            continue

        for tc in chunk.tool_call_chunks:  # type: ignore[attr-defined]
            if not isinstance(tc, dict):
                continue

            # Use explicit index if provided, default to 0
            tc_index = tc.get("index", 0)

            if tc_index not in tool_calls_by_index:
                tool_calls_by_index[tc_index] = {
                    "name": "",
                    "args": "",  # Initialize as empty STRING, not dict
                    "id": None,
                    "type": "tool_call",
                }

            # Concatenate string fields from chunks
            if tc.get("name"):
                tool_calls_by_index[tc_index]["name"] = tc["name"]
            if tc.get("id"):
                tool_calls_by_index[tc_index]["id"] = tc["id"]
            if tc.get("args"):
                # Concatenate args as strings (e.g., '{"' + 'command' + '":"' ...)
                tool_calls_by_index[tc_index]["args"] += tc["args"]

    # Parse the concatenated JSON args strings into dicts
    tool_calls = []
    for tc_data in tool_calls_by_index.values():
        args_str = tc_data["args"]
        try:
            # Parse accumulated JSON string into dict
            import json

            parsed_args = json.loads(args_str) if args_str else {}
            tool_calls.append(
                {
                    "name": tc_data["name"],
                    "args": parsed_args,
                    "id": tc_data["id"],
                    "type": "tool_call",
                }
            )
        except json.JSONDecodeError:
            # If parsing fails, include with empty args
            tool_calls.append(
                {
                    "name": tc_data["name"],
                    "args": {},
                    "id": tc_data["id"],
                    "type": "tool_call",
                }
            )

    # Create final message with aggregated content and tool_calls
    return AIMessage(
        content="".join(content_parts),
        tool_calls=tool_calls if tool_calls else [],
    )


def stream_chunks(
    model: BaseChatModel,
    messages: list[BaseMessage],
) -> Iterator[StreamChunk]:
    """Stream AI response as raw chunks without UI dependencies.

    Core streaming function decoupled from presentation layer. Yields StreamChunk
    objects containing token content without any Rich/console rendering.
    Suitable for headless SDK usage, web backends, or custom presentation layers.

    Args:
        model: LangChain chat model with .stream() support.
        messages: Conversation messages as LangChain BaseMessage objects.

    Yields:
        StreamChunk objects with content and metadata for each token.

    Raises:
        StreamingError: If streaming fails or is interrupted.

    Example:
        >>> from consoul.ai import get_chat_model, stream_chunks
        >>> model = get_chat_model("gpt-4o")
        >>> messages = [{"role": "user", "content": "Count to 5"}]
        >>> for chunk in stream_chunks(model, messages):
        ...     print(chunk.content, end="", flush=True)
        1, 2, 3, 4, 5

    Note:
        For Rich-formatted output in CLI/TUI, use consoul.presentation.display_stream_with_rich().
        For async streaming, use consoul.ai.async_streaming.async_stream_events().
    """
    try:
        for chunk in model.stream(messages):
            # Skip empty chunks (some providers send metadata chunks)
            if not chunk.content:
                continue

            # Handle both string and complex content
            token = (
                chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            )

            yield StreamChunk(
                content=token,
                tokens=0,  # Token counting can be added later if needed
                cost=0.0,  # Cost calculation can be added later if needed
                metadata={},  # Provider-specific metadata can be added here
            )

    except KeyboardInterrupt:
        raise StreamingError(
            "Streaming interrupted by user", partial_response=""
        ) from KeyboardInterrupt()

    except Exception as e:
        raise StreamingError(f"Streaming failed: {e}", partial_response="") from e


def stream_response(
    model: BaseChatModel,
    messages: list[BaseMessage],
    console: Any = None,  # Rich Console instance (lazy imported)
    show_prefix: bool = True,
    show_spinner: bool = True,
    render_markdown: bool = True,
) -> tuple[str, AIMessage]:
    """Stream AI response with Rich formatting (DEPRECATED).

    .. deprecated:: 0.3.0
        Use :func:`stream_chunks` for headless streaming or
        :func:`consoul.presentation.display_stream_with_rich` for Rich formatting.
        This function will be removed in version 1.0.0.

    Streams tokens from the model with Rich-based progress indicator and markdown rendering.
    Maintained for backward compatibility with existing CLI/TUI code.

    Args:
        model: LangChain chat model with .stream() support.
        messages: Conversation messages as LangChain BaseMessage objects.
        console: Rich console for output. Creates default if None.
        show_prefix: Whether to print "Assistant: " prefix.
        show_spinner: Whether to show spinner progress indicator during streaming.
        render_markdown: Whether to render response as markdown with syntax highlighting.

    Returns:
        Tuple of (complete response text, final AIMessage with tool_calls if any).

    Raises:
        StreamingError: If streaming fails or is interrupted.

    Example (Deprecated):
        >>> model = get_chat_model("claude-3-5-sonnet-20241022")
        >>> messages = [{"role": "user", "content": "Count to 5"}]
        >>> response_text, ai_message = stream_response(model, messages)  # Deprecated
        Assistant: 1, 2, 3, 4, 5

    Recommended Migration:
        >>> # For headless/SDK usage:
        >>> from consoul.ai import stream_chunks
        >>> for chunk in stream_chunks(model, messages):
        ...     print(chunk.content, end="")
        >>>
        >>> # For CLI/TUI with Rich formatting:
        >>> from consoul.presentation import display_stream_with_rich
        >>> chunks = stream_chunks(model, messages)
        >>> response = display_stream_with_rich(chunks)
    """
    # Emit deprecation warning
    warnings.warn(
        "stream_response() is deprecated and will be removed in version 1.0.0. "
        "Use stream_chunks() for headless streaming or "
        "consoul.presentation.display_stream_with_rich() for Rich formatting.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Lazy import Rich dependencies (only when this deprecated function is called)
    from rich.console import Console
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.spinner import Spinner
    from rich.text import Text

    if console is None:
        console = Console()

    collected_tokens: list[str] = []
    collected_chunks: list[AIMessage] = []  # Collect chunks for tool_calls
    prefix = "Assistant: " if show_prefix else ""

    try:
        if show_spinner:
            # Use Live display with spinner for progress indication
            spinner = Spinner("dots", text="Waiting for response...")
            with Live(spinner, console=console, refresh_per_second=10) as live:
                for chunk in model.stream(messages):
                    # Collect all chunks (even empty ones) for tool_calls reconstruction
                    collected_chunks.append(chunk)

                    # Skip empty chunks for display (some providers send metadata chunks)
                    if not chunk.content:
                        continue

                    # Handle both string and complex content
                    token = (
                        chunk.content
                        if isinstance(chunk.content, str)
                        else str(chunk.content)
                    )
                    collected_tokens.append(token)

                    # If rendering markdown, just show spinner (no text accumulation)
                    # Otherwise show accumulated text during streaming
                    if not render_markdown:
                        response_text = Text()
                        if prefix and collected_tokens:
                            response_text.append(prefix, style="bold cyan")
                        response_text.append("".join(collected_tokens))
                        live.update(response_text, refresh=True)

            # After live display ends, render as markdown if enabled
            if render_markdown and collected_tokens:
                # Live display showed only spinner, now show the markdown-rendered version
                if show_prefix:
                    console.print("[bold cyan]Assistant:[/bold cyan]")
                md = Markdown("".join(collected_tokens))
                console.print(md)
            else:
                # No markdown, just add final newline
                console.print()
        else:
            # Fallback to simple token-by-token printing without spinner
            first_token = True
            for chunk in model.stream(messages):
                # Collect all chunks (even empty ones) for tool_calls reconstruction
                collected_chunks.append(chunk)

                # Skip empty chunks for display (some providers send metadata chunks)
                if not chunk.content:
                    continue

                # Show prefix before first token
                if first_token and show_prefix:
                    console.print("Assistant: ", end="")
                    first_token = False

                # Handle both string and complex content
                token = (
                    chunk.content
                    if isinstance(chunk.content, str)
                    else str(chunk.content)
                )
                collected_tokens.append(token)
                console.print(token, end="")

            # Render accumulated response as markdown if enabled
            if render_markdown and collected_tokens:
                console.print("\n")  # Add spacing
                if show_prefix:
                    console.print("[bold cyan]Assistant:[/bold cyan]")
                md = Markdown("".join(collected_tokens))
                console.print(md)
            else:
                # Final newline after complete response
                if collected_tokens:
                    console.print()

        # Reconstruct final AIMessage with tool_calls
        final_message = _reconstruct_ai_message(collected_chunks)
        return "".join(collected_tokens), final_message

    except KeyboardInterrupt:
        # Graceful handling of Ctrl+C - preserve partial response
        partial_response = "".join(collected_tokens)
        console.print("\n[yellow]⚠ Interrupted[/yellow]")
        # Wrap in StreamingError to preserve partial response for caller
        raise StreamingError(
            "Streaming interrupted by user", partial_response=partial_response
        ) from KeyboardInterrupt()

    except Exception as e:
        # Preserve partial response for debugging/recovery
        partial_response = "".join(collected_tokens)
        console.print(f"\n[red]❌ Streaming error: {e}[/red]")
        raise StreamingError(
            f"Streaming failed: {e}", partial_response=partial_response
        ) from e
