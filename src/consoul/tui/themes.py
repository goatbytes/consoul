"""Consoul brand themes for Textual TUI.

This module defines the official Consoul brand themes as Textual Theme objects.
"""

from __future__ import annotations

from textual.theme import Theme

__all__ = [
    "CONSOUL_DARK",
    "CONSOUL_LIGHT",
    "CONSOUL_OLED",
    "CONSOUL_MIDNIGHT",
    "CONSOUL_MATRIX",
    "CONSOUL_SUNSET",
    "CONSOUL_OCEAN",
    "CONSOUL_VOLCANO",
    "CONSOUL_NEON",
    "CONSOUL_FOREST",
]

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

# Consoul OLED Theme - True black for OLED displays with vibrant accents
CONSOUL_OLED = Theme(
    name="consoul-oled",
    primary="#00B4FF",  # Bright Sky Blue - vibrant on OLED
    secondary="#FF8C00",  # Bright Orange - secondary actions
    warning="#FFD700",  # Gold - warnings
    error="#FF4444",  # Bright Red - errors
    success="#00FF88",  # Bright Green - success states
    accent="#00B4FF",  # Bright Sky Blue - highlights
    foreground="#FFFFFF",  # Pure White - maximum contrast
    background="#000000",  # True Black - OLED power saving
    surface="#0A0A0A",  # Near black - subtle elevation
    panel="#121212",  # Very dark gray - panels with minimal contrast
    dark=True,
    variables={
        "text-muted": "#B0B0B0",  # Light gray - secondary text
        "button-color-foreground": "#FFFFFF",
        "footer-background": "#00B4FF",
        "footer-key-foreground": "#000000",
        "footer-description-foreground": "#000000",
        "block-cursor-foreground": "#000000",
        "block-cursor-background": "#00B4FF",
        "input-selection-background": "#00B4FF 35%",
    },
)

# Consoul Midnight Theme - Deep navy for late-night coding
CONSOUL_MIDNIGHT = Theme(
    name="consoul-midnight",
    primary="#88D4F5",  # Soft cyan - soothing primary
    secondary="#FFB347",  # Warm amber - secondary actions
    warning="#FFA726",  # Soft orange - warnings
    error="#EF5350",  # Soft red - errors
    success="#66BB6A",  # Soft green - success states
    accent="#88D4F5",  # Soft cyan - highlights
    foreground="#E0E7F1",  # Light blue-gray - easy on eyes
    background="#0B1420",  # Deep navy - midnight sky
    surface="#152238",  # Lighter navy - elevated surfaces
    panel="#1A2B45",  # Medium navy - panels
    dark=True,
    variables={
        "text-muted": "#7B8FA3",  # Muted blue-gray - secondary text
        "button-color-foreground": "#0B1420",
        "footer-background": "#88D4F5",
        "footer-key-foreground": "#0B1420",
        "footer-description-foreground": "#0B1420",
        "block-cursor-foreground": "#0B1420",
        "block-cursor-background": "#88D4F5",
        "input-selection-background": "#88D4F5 35%",
    },
)

# Consoul Matrix Theme - Classic hacker green
CONSOUL_MATRIX = Theme(
    name="consoul-matrix",
    primary="#00FF00",  # Bright green - matrix primary
    secondary="#00CC00",  # Medium green - secondary actions
    warning="#FFFF00",  # Yellow - warnings
    error="#FF0000",  # Red - errors
    success="#00FF00",  # Bright green - success states
    accent="#00FF00",  # Bright green - highlights
    foreground="#00FF00",  # Bright green - matrix text
    background="#000000",  # True black - void
    surface="#001100",  # Very dark green - subtle elevation
    panel="#002200",  # Dark green - panels
    dark=True,
    variables={
        "text-muted": "#00AA00",  # Medium green - secondary text
        "button-color-foreground": "#000000",
        "footer-background": "#00FF00",
        "footer-key-foreground": "#000000",
        "footer-description-foreground": "#000000",
        "block-cursor-foreground": "#000000",
        "block-cursor-background": "#00FF00",
        "input-selection-background": "#00FF00 35%",
    },
)

# Consoul Sunset Theme - Warm purple and orange evening vibes
CONSOUL_SUNSET = Theme(
    name="consoul-sunset",
    primary="#FF8474",  # Coral/peach - warm primary
    secondary="#FFB347",  # Warm amber - secondary actions
    warning="#FFA726",  # Orange - warnings
    error="#EF5350",  # Soft red - errors
    success="#AED581",  # Soft lime - success states
    accent="#FF8474",  # Coral/peach - highlights
    foreground="#FFF4E6",  # Warm white - comfortable text
    background="#2D1B2E",  # Deep purple - sunset sky
    surface="#3D2942",  # Purple-gray - elevated surfaces
    panel="#4A3356",  # Medium purple - panels
    dark=True,
    variables={
        "text-muted": "#C8A2C8",  # Lavender - secondary text
        "button-color-foreground": "#2D1B2E",
        "footer-background": "#FF8474",
        "footer-key-foreground": "#2D1B2E",
        "footer-description-foreground": "#2D1B2E",
        "block-cursor-foreground": "#2D1B2E",
        "block-cursor-background": "#FF8474",
        "input-selection-background": "#FF8474 35%",
    },
)

# Consoul Ocean Theme - Deep blue and teal tranquility
CONSOUL_OCEAN = Theme(
    name="consoul-ocean",
    primary="#14B8A6",  # Teal - ocean primary
    secondary="#22D3EE",  # Cyan - secondary actions
    warning="#F59E0B",  # Amber - warnings
    error="#EF4444",  # Red - errors
    success="#10B981",  # Emerald - success states
    accent="#14B8A6",  # Teal - highlights
    foreground="#F0FDFA",  # Very light cyan - crisp text
    background="#0A1929",  # Deep ocean blue - depths
    surface="#0F2942",  # Medium ocean blue - elevated surfaces
    panel="#163D5A",  # Lighter ocean blue - panels
    dark=True,
    variables={
        "text-muted": "#6B9EC4",  # Muted blue - secondary text
        "button-color-foreground": "#0A1929",
        "footer-background": "#14B8A6",
        "footer-key-foreground": "#0A1929",
        "footer-description-foreground": "#0A1929",
        "block-cursor-foreground": "#0A1929",
        "block-cursor-background": "#14B8A6",
        "input-selection-background": "#14B8A6 35%",
    },
)

# Consoul Volcano Theme - Charcoal with lava accents
CONSOUL_VOLCANO = Theme(
    name="consoul-volcano",
    primary="#FF6B35",  # Lava orange - volcanic primary
    secondary="#F7931E",  # Bright orange - secondary actions
    warning="#FFC300",  # Yellow - warnings
    error="#C1121F",  # Deep red - errors
    success="#52B788",  # Forest green - success states
    accent="#FF6B35",  # Lava orange - highlights
    foreground="#FFF8F0",  # Warm white - comfortable text
    background="#1A1A1D",  # Dark charcoal - volcanic rock
    surface="#2A2A2D",  # Medium charcoal - elevated surfaces
    panel="#3A3A3D",  # Light charcoal - panels
    dark=True,
    variables={
        "text-muted": "#B0B0B5",  # Light gray - secondary text
        "button-color-foreground": "#1A1A1D",
        "footer-background": "#FF6B35",
        "footer-key-foreground": "#1A1A1D",
        "footer-description-foreground": "#1A1A1D",
        "block-cursor-foreground": "#1A1A1D",
        "block-cursor-background": "#FF6B35",
        "input-selection-background": "#FF6B35 35%",
    },
)

# Consoul Neon Theme - Cyberpunk synthwave aesthetic
CONSOUL_NEON = Theme(
    name="consoul-neon",
    primary="#FF10F0",  # Hot pink - neon primary
    secondary="#00FFFF",  # Electric cyan - secondary actions
    warning="#FFFF00",  # Electric yellow - warnings
    error="#FF0055",  # Hot red - errors
    success="#39FF14",  # Neon green - success states
    accent="#FF10F0",  # Hot pink - highlights
    foreground="#FFFFFF",  # Pure white - maximum contrast
    background="#000000",  # Pure black - void
    surface="#0D0D0D",  # Near black - subtle elevation
    panel="#1A1A1A",  # Dark gray - panels
    dark=True,
    variables={
        "text-muted": "#B0B0B0",  # Light gray - secondary text
        "button-color-foreground": "#000000",
        "footer-background": "#FF10F0",
        "footer-key-foreground": "#000000",
        "footer-description-foreground": "#000000",
        "block-cursor-foreground": "#000000",
        "block-cursor-background": "#FF10F0",
        "input-selection-background": "#FF10F0 35%",
    },
)

# Consoul Forest Theme - Natural green and earth tones
CONSOUL_FOREST = Theme(
    name="consoul-forest",
    primary="#7CB342",  # Moss green - forest primary
    secondary="#8D6E63",  # Earth brown - secondary actions
    warning="#FFA726",  # Autumn orange - warnings
    error="#D32F2F",  # Deep red - errors
    success="#66BB6A",  # Leaf green - success states
    accent="#7CB342",  # Moss green - highlights
    foreground="#E8F5E9",  # Very light green - natural text
    background="#0D1F1A",  # Deep forest green - woodland
    surface="#1A2F28",  # Medium forest green - elevated surfaces
    panel="#263F35",  # Lighter forest green - panels
    dark=True,
    variables={
        "text-muted": "#81C784",  # Soft green - secondary text
        "button-color-foreground": "#0D1F1A",
        "footer-background": "#7CB342",
        "footer-key-foreground": "#0D1F1A",
        "footer-description-foreground": "#0D1F1A",
        "block-cursor-foreground": "#0D1F1A",
        "block-cursor-background": "#7CB342",
        "input-selection-background": "#7CB342 35%",
    },
)
