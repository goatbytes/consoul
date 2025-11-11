"""TUI tools integration module.

This package contains TUI-specific implementations for tool calling features,
including approval providers that integrate with Textual modals.
"""

from __future__ import annotations

from consoul.tui.tools.approval import TuiApprovalProvider

__all__ = ["TuiApprovalProvider"]
