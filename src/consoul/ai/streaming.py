"""Streaming response handling for AI chat models.

This module provides utilities for streaming responses from AI models
token-by-token with real-time display, progress indicators, and graceful
interrupt handling.

Example:
    >>> from consoul.ai import get_chat_model, stream_response
    >>> model = get_chat_model("gpt-4o", api_key="...")
    >>> messages = [{"role": "user", "content": "Hello!"}]
    >>> response_text, ai_message = stream_response(model, messages)
    Assistant: Hello! How can I help you today?
    >>> print(response_text)
    Hello! How can I help you today?
    >>> print(ai_message.tool_calls)
    []
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text

from consoul.ai.exceptions import StreamingError

if TYPE_CHECKING:
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


def stream_response(
    model: BaseChatModel,
    messages: list[BaseMessage],
    console: Console | None = None,
    show_prefix: bool = True,
    show_spinner: bool = True,
    render_markdown: bool = True,
) -> tuple[str, AIMessage]:
    """Stream AI response with real-time token-by-token display and progress indicator.

    Streams tokens from the model as they are generated, displaying them
    in real-time to the console with a spinner progress indicator. Handles
    keyboard interrupts gracefully and preserves partial responses in case of errors.

    Args:
        model: LangChain chat model with .stream() support.
        messages: Conversation messages as LangChain BaseMessage objects.
        console: Rich console for output. Creates default if None.
        show_prefix: Whether to print "Assistant: " prefix.
        show_spinner: Whether to show spinner progress indicator during streaming.
        render_markdown: Whether to render response as markdown with syntax highlighting.

    Returns:
        Tuple of (complete response text, final AIMessage with tool_calls if any).
        The AIMessage contains tool_calls attribute for tool execution workflows.

    Raises:
        StreamingError: If streaming fails or is interrupted, includes partial response.
            - Message "Streaming interrupted by user" indicates KeyboardInterrupt (Ctrl+C)
            - Other messages indicate actual errors during streaming

    Example:
        >>> model = get_chat_model("claude-3-5-sonnet-20241022")
        >>> messages = [{"role": "user", "content": "Count to 5"}]
        >>> response_text, ai_message = stream_response(model, messages)
        Assistant: 1, 2, 3, 4, 5
        >>> response_text
        '1, 2, 3, 4, 5'
        >>> ai_message.tool_calls
        []

    Note:
        The function collects all chunks into a list before joining them
        to preserve the complete response even if streaming is interrupted.
        Chunks are aggregated to reconstruct tool_calls from the final AIMessage.
    """
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

                    # Update live display with accumulated response (plain text during streaming)
                    # We'll render markdown after streaming completes
                    response_text = Text()
                    if prefix and collected_tokens and not render_markdown:
                        # Only show prefix during streaming if not rendering markdown
                        # (markdown will show it after)
                        response_text.append(prefix, style="bold cyan")
                    response_text.append("".join(collected_tokens))

                    live.update(response_text, refresh=True)

            # After live display ends, render as markdown if enabled
            if render_markdown and collected_tokens:
                # Live display has ended, now show the final markdown-rendered version
                console.print()  # Clear line after live display
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
