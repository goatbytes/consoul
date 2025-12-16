"""Tool execution status enumeration.

Defines standard status values for tool execution lifecycle,
used by TUI widgets to display execution state visually.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["ToolStatus"]


class ToolStatus(Enum):
    """Tool execution status with visual indicators.

    Each status includes an emoji for visual representation in the TUI.

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
