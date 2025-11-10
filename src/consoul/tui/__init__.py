"""Consoul Terminal User Interface (TUI) module.

This module provides a beautiful, keyboard-driven TUI for interactive AI
conversations using the Textual framework.

Note: This module is optional and can be excluded when using Consoul as a
library (e.g., in Gira). Core AI functionality is in consoul.ai.
"""

from __future__ import annotations

from consoul.tui.app import ConsoulApp
from consoul.tui.config import TuiConfig

__all__ = ["ConsoulApp", "TuiConfig"]
