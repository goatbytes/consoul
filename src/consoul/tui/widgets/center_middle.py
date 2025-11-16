"""CenterMiddle widget for centering content both horizontally and vertically.

This module provides a simple container that centers its children on both axes.
Useful for empty states, loading indicators, and centered messages.
"""

from textual.widget import Widget

__all__ = ["CenterMiddle"]


class CenterMiddle(Widget, inherit_bindings=False):
    """A container which aligns children on both axes.

    Centers child widgets both horizontally and vertically within the
    available space. Commonly used for empty states and centered messages.

    Example:
        ```python
        with CenterMiddle():
            yield Label("No items to display")
        ```
    """

    DEFAULT_CSS = """
    CenterMiddle {
        align: center middle;
        width: 1fr;
        height: 1fr;
    }
    """
