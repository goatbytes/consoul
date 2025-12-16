"""Utilities for reading from stdin in CLI commands."""

import sys

# Maximum bytes to read from stdin (1MB)
DEFAULT_MAX_SIZE = 1024 * 1024


def read_stdin(max_size: int = DEFAULT_MAX_SIZE) -> str | None:
    """Read content from stdin with size limit.

    Args:
        max_size: Maximum bytes to read (default 1MB)

    Returns:
        Stdin content as string, or None if no data available

    Raises:
        ValueError: If stdin exceeds size limit or cannot be decoded

    Example:
        >>> content = read_stdin()
        >>> if content:
        ...     print(f"Read {len(content)} bytes")
    """
    # Check if stdin is a tty (interactive terminal)
    if sys.stdin.isatty():
        return None

    # Read stdin content with size limit
    # Read one extra byte to detect if size limit exceeded
    content = sys.stdin.buffer.read(max_size + 1)

    # Check size limit
    if len(content) > max_size:
        size_mb = max_size / (1024 * 1024)
        raise ValueError(
            f"Stdin content exceeds maximum size of {size_mb:.1f}MB. "
            f"Consider filtering or summarizing the input first."
        )

    # Handle empty stdin
    if not content:
        return None

    # Decode with error handling
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(
            f"Stdin contains invalid UTF-8 data: {e}. Binary content is not supported."
        ) from e


def format_stdin_message(stdin_content: str, user_message: str) -> str:
    """Format message with stdin content prepended.

    The formatted message clearly separates stdin content from the user's
    question using XML-style tags, helping the AI understand the context
    structure.

    Args:
        stdin_content: Content read from stdin
        user_message: User's question or prompt

    Returns:
        Formatted message with stdin in context

    Example:
        >>> stdin = "git diff output..."
        >>> question = "Review this diff"
        >>> msg = format_stdin_message(stdin, question)
        >>> print(msg)
        <stdin>
        git diff output...
        </stdin>

        Review this diff
    """
    return f"""<stdin>
{stdin_content}
</stdin>

{user_message}"""
