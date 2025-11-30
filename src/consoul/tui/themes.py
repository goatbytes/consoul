"""Consoul brand themes for Textual TUI.

This module defines the official Consoul brand themes as Textual Theme objects.
"""

from __future__ import annotations

from textual.theme import Theme

__all__ = ["CONSOUL_DARK", "CONSOUL_LIGHT"]

# Consoul Dark Theme - Binary Slate with Sky Blue accents
CONSOUL_DARK = Theme(
    name="consoul-dark",
    primary="#0085CC",  # Sky Blue - innovation and trust
    secondary="#FF6600",  # Deep purple - secondary actions
    warning="#FFC107",  # Amber - warnings
    error="#DC3545",  # Red - errors
    success="#28A745",  # Green - success states
    accent="#0085CC",  # Sky Blue - highlights
    foreground="#FFFFFF",  # Pure White - main text
    background="#2A2A2A",  # Darker than Binary Slate for depth
    surface="#3D3D3D",  # Binary Slate - elevated surfaces
    panel="#3D3D3D",  # Binary Slate - panels
    dark=True,
    variables={
        "text-muted": "#9BA3AB",  # Light gray - secondary text
        "button-color-foreground": "#FFFFFF",
        "footer-background": "#0085CC",
        "footer-key-foreground": "#FFFFFF",
        "block-cursor-foreground": "#2A2A2A",
        "block-cursor-background": "#0085CC",
        "input-selection-background": "#0085CC 35%",
    },
)

# Consoul Light Theme - Pure White with Sky Blue primary
CONSOUL_LIGHT = Theme(
    name="consoul-light",
    primary="#0085CC",  # Sky Blue - innovation and trust
    secondary="#CC4300",  # Deep purple - secondary actions
    warning="#FFC107",  # Amber - warnings
    error="#DC3545",  # Red - errors
    success="#28A745",  # Green - success states
    accent="#0085CC",  # Sky Blue - highlights
    foreground="#3D3D3D",  # Binary Slate - main text
    background="#FFFFFF",  # Pure White - base background
    surface="#F8F9FA",  # Very light gray - panels
    panel="#F5F5F5",  # Slightly off-white for contrast
    dark=False,
    variables={
        "text-muted": "#6C757D",  # Medium gray - secondary text for light theme
        "button-color-foreground": "#FFFFFF",
        "footer-background": "#0085CC",
        "footer-key-foreground": "#FFFFFF",
        "footer-description-foreground": "#FFFFFF",
        "block-cursor-foreground": "#FFFFFF",
        "block-cursor-background": "#0085CC",
        "input-selection-background": "#0085CC 35%",
    },
)
