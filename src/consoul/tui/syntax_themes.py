"""Shared syntax highlighting theme mappings for Consoul.

This module provides the single source of truth for mapping Consoul themes
to Pygments syntax highlighting styles used across the TUI.
"""

from __future__ import annotations

__all__ = ["THEME_SYNTAX_MAP"]

# Map Consoul themes to Pygments syntax highlighting styles
THEME_SYNTAX_MAP = {
    "consoul-dark": "monokai",
    "consoul-light": "xcode",  # Pure white background, better than friendly (#f0f0f0)
    "consoul-oled": "github-dark",
    "consoul-midnight": "nord",
    "consoul-matrix": "monokai",  # Green syntax works well with matrix theme
    "consoul-sunset": "dracula",
    "consoul-ocean": "material",
    "consoul-volcano": "monokai",
    "consoul-neon": "fruity",  # Vibrant colors perfect for cyberpunk/neon aesthetic
    "consoul-forest": "gruvbox-dark",
}
