"""Streaming response handling for AI chat models.

This module provides utilities for streaming responses from AI models
token-by-token with real-time display, progress indicators, and graceful
interrupt handling.

Example:
    >>> from consoul.ai import get_chat_model, stream_response
    >>> model = get_chat_model("gpt-4o", api_key="...")
    >>> messages = [{"role": "user", "content": "Hello!"}]
    >>> response = stream_response(model, messages)
    Assistant: Hello! How can I help you today?
    >>> print(response)
    Hello! How can I help you today?
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
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage


def stream_response(
    model: BaseChatModel,
    messages: list[BaseMessage],
    console: Console | None = None,
    show_prefix: bool = True,
    show_spinner: bool = True,
    render_markdown: bool = True,
) -> str:
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
        Complete response text from the model.

    Raises:
        StreamingError: If streaming fails or is interrupted, includes partial response.
            - Message "Streaming interrupted by user" indicates KeyboardInterrupt (Ctrl+C)
            - Other messages indicate actual errors during streaming

    Example:
        >>> model = get_chat_model("claude-3-5-sonnet-20241022")
        >>> messages = [{"role": "user", "content": "Count to 5"}]
        >>> response = stream_response(model, messages)
        Assistant: 1, 2, 3, 4, 5
        >>> response
        '1, 2, 3, 4, 5'

    Note:
        The function collects all tokens into a list before joining them
        to preserve the complete response even if streaming is interrupted.
    """
    if console is None:
        console = Console()

    collected_tokens: list[str] = []
    prefix = "Assistant: " if show_prefix else ""

    try:
        if show_spinner:
            # Use Live display with spinner for progress indication
            spinner = Spinner("dots", text="Waiting for response...")
            with Live(spinner, console=console, refresh_per_second=10) as live:
                for chunk in model.stream(messages):
                    # Skip empty chunks (some providers send metadata chunks)
                    if not chunk.content:
                        continue

                    # Handle both string and complex content
                    token = (
                        chunk.content
                        if isinstance(chunk.content, str)
                        else str(chunk.content)
                    )
                    collected_tokens.append(token)

                    # Update live display with accumulated response
                    response_text = Text()
                    if prefix and collected_tokens:
                        response_text.append(prefix, style="bold cyan")
                    response_text.append("".join(collected_tokens))

                    live.update(response_text, refresh=True)

            # Render accumulated response as markdown if enabled
            if render_markdown and collected_tokens:
                console.print()  # Clear the live display
                if show_prefix:
                    console.print("[bold cyan]Assistant:[/bold cyan]")
                md = Markdown("".join(collected_tokens))
                console.print(md)
            else:
                # Print final newline after live display ends
                console.print()
        else:
            # Fallback to simple token-by-token printing without spinner
            first_token = True
            for chunk in model.stream(messages):
                # Skip empty chunks (some providers send metadata chunks)
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

        return "".join(collected_tokens)

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
