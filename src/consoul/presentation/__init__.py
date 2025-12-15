"""Presentation layer for console output formatting.

This package provides UI/display utilities separated from business logic,
allowing for optional dependencies and headless SDK usage.

Modules:
    rich_display: Rich-based formatting for streaming responses
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "display_stream_with_rich",
]


# Lazy import - Rich is optional for SDK users
def __getattr__(name: str) -> Any:
    """Lazy import of presentation utilities."""
    if name == "display_stream_with_rich":
        from consoul.presentation.rich_display import display_stream_with_rich

        return display_stream_with_rich
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
