"""Consoul Terminal User Interface (TUI) module.

This module provides a beautiful, keyboard-driven TUI for interactive AI
conversations using the Textual framework.

Note: This module is optional and can be excluded when using Consoul as a
library (e.g., in Gira). Core AI functionality is in consoul.ai.
"""

from __future__ import annotations

from consoul.tui.animations import AnimationStyle, BinaryAnimator
from consoul.tui.app import ConsoulApp
from consoul.tui.config import TuiConfig
from consoul.tui.loading import BinaryCanvas, ConsoulLoadingScreen, LoadingScreen

__all__ = [
    "AnimationStyle",
    "BinaryAnimator",
    "BinaryCanvas",
    "ConsoulApp",
    "ConsoulLoadingScreen",
    "LoadingScreen",
    "TuiConfig",
]
