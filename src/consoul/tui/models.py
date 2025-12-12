"""TUI data models for display layer.

This module contains simple dataclasses and enums used by TUI widgets.
These decouple the UI presentation layer from SDK internal types and business logic.

Architecture Principle:
    - SDK Layer: Complex types, business logic, LangChain integration
    - TUI Layer: Simple display models, UI rendering, Textual widgets
    - Conversion happens at app.py boundary (SDK → TUI models before passing to widgets)

Usage:
    >>> from consoul.tui.models import ToolStatus
    >>> status = ToolStatus.SUCCESS
    >>> print(status.value)
    '✓ Completed'
"""

from __future__ import annotations

from enum import Enum

__all__ = ["ToolStatus"]


class ToolStatus(Enum):
    """Tool execution status for TUI display.

    Each status includes an emoji for visual representation in the TUI.
    Used by ToolCallWidget and tool execution displays.

    Lifecycle:
        PENDING → EXECUTING → SUCCESS/ERROR/DENIED

    Example:
        >>> status = ToolStatus.PENDING
        >>> print(status.value)
        '⏳ Awaiting approval'
        >>> status = ToolStatus.SUCCESS
        >>> print(status.value)
        '✓ Completed'
    """

    PENDING = "⏳ Awaiting approval"
    EXECUTING = "⚙️ Executing..."
    SUCCESS = "✓ Completed"
    ERROR = "✗ Failed"
    DENIED = "🚫 Denied"

    def __str__(self) -> str:
        """Return status value as string."""
        return self.value
