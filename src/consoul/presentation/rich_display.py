"""Rich-based display utilities for streaming AI responses.

Extracted from consoul.ai.streaming to separate presentation from business logic.
Requires Rich library - not needed for headless SDK usage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Iterator

    from consoul.ai.models import StreamChunk


def display_stream_with_rich(
    chunks: Iterator[StreamChunk],
    console: Console | None = None,
    show_prefix: bool = True,
    show_spinner: bool = True,
    render_markdown: bool = True,
) -> str:
    """Display streaming chunks with Rich formatting.

    Applies Rich-based formatting (spinner, markdown, colored output) to
    stream chunks. This is the presentation layer separated from core streaming logic.

    Args:
        chunks: Iterator of StreamChunk objects to display
        console: Rich console for output. Creates default if None.
        show_prefix: Whether to print "Assistant: " prefix.
        show_spinner: Whether to show spinner progress indicator during streaming.
        render_markdown: Whether to render response as markdown with syntax highlighting.

    Returns:
        Complete response text after streaming finishes.

    Example:
        >>> from consoul.ai.streaming import stream_chunks
        >>> from consoul.presentation import display_stream_with_rich
        >>>
        >>> chunks = stream_chunks(model, messages)
        >>> response = display_stream_with_rich(chunks)
        Assistant: Hello! How can I help you?

    Note:
        This function handles all Rich-specific rendering:
        - Live display with spinner during streaming
        - Markdown rendering with syntax highlighting
        - Colored prefix and progress indicators
        - Token-by-token display with proper formatting
    """
    if console is None:
        console = Console()

    collected_tokens: list[str] = []
    prefix = "Assistant: " if show_prefix else ""

    if show_spinner:
        # Use Live display with spinner for progress indication
        spinner = Spinner("dots", text="Waiting for response...")
        with Live(spinner, console=console, refresh_per_second=10) as live:
            for chunk in chunks:
                collected_tokens.append(chunk.content)

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
        for chunk in chunks:
            # Show prefix before first token
            if first_token and show_prefix:
                console.print("Assistant: ", end="")
                first_token = False

            collected_tokens.append(chunk.content)
            console.print(chunk.content, end="")

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
