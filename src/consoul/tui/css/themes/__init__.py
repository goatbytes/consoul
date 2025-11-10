"""Theme management for Consoul TUI.

This module provides utilities for loading and managing color themes.
Themes are defined as TCSS files with CSS variable definitions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

__all__ = [
    "ThemeName",
    "get_available_themes",
    "get_theme_path",
    "load_theme",
]

# Available theme names
ThemeName = Literal["monokai", "dracula", "nord", "gruvbox"]


def get_theme_path(theme: ThemeName) -> Path:
    """Get the file path for a theme's TCSS file.

    Args:
        theme: Name of the theme

    Returns:
        Path to the theme's TCSS file

    Example:
        >>> path = get_theme_path("monokai")
        >>> print(path.name)
        monokai.tcss
    """
    themes_dir = Path(__file__).parent
    return themes_dir / f"{theme}.tcss"


def load_theme(theme: ThemeName) -> str:
    """Load a theme's CSS content from its TCSS file.

    Args:
        theme: Name of the theme to load

    Returns:
        CSS content as a string

    Raises:
        FileNotFoundError: If the theme file doesn't exist

    Example:
        >>> css = load_theme("monokai")
        >>> "$primary: #F92672" in css
        True
    """
    theme_path = get_theme_path(theme)
    if not theme_path.exists():
        msg = f"Theme file not found: {theme_path}"
        raise FileNotFoundError(msg)
    return theme_path.read_text(encoding="utf-8")


def get_available_themes() -> list[str]:
    """Get a list of all available theme names.

    Returns:
        List of theme names (without .tcss extension)

    Example:
        >>> themes = get_available_themes()
        >>> "monokai" in themes
        True
        >>> len(themes) >= 4
        True
    """
    return ["monokai", "dracula", "nord", "gruvbox"]
