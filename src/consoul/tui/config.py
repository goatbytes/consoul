"""TUI-specific configuration models.

This module defines Pydantic configuration models for Consoul's Textual TUI,
covering appearance, performance tuning, and behavior settings.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = ["TuiConfig"]


class TuiConfig(BaseModel):
    """TUI-specific configuration.

    Controls appearance, behavior, and performance of the Textual TUI.
    These settings are independent of core AI configuration.
    """

    # Theme and Appearance
    theme: str = Field(default="monokai", description="TUI color theme")
    show_sidebar: bool = Field(
        default=True, description="Show conversation list sidebar"
    )
    sidebar_width: str = Field(default="30%", description="Sidebar width (CSS units)")
    show_timestamps: bool = Field(default=True, description="Show message timestamps")
    show_token_count: bool = Field(
        default=True, description="Show token usage in messages"
    )

    # Performance
    gc_mode: Literal["auto", "manual", "streaming-aware"] = Field(
        default="streaming-aware", description="Garbage collection strategy"
    )
    gc_interval_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=300.0,
        description="Interval for idle GC (manual/streaming-aware modes)",
    )
    gc_generation: int = Field(
        default=0,
        ge=0,
        le=2,
        description="GC generation to collect (0=young, 1=middle, 2=all)",
    )

    # Streaming Behavior
    stream_buffer_size: int = Field(
        default=200,
        ge=50,
        le=1000,
        description="Characters to buffer before rendering",
    )
    stream_debounce_ms: int = Field(
        default=150,
        ge=50,
        le=500,
        description="Milliseconds to debounce markdown renders",
    )
    stream_renderer: Literal["markdown", "richlog", "hybrid"] = Field(
        default="markdown", description="Widget type for streaming responses"
    )

    # Conversation List
    initial_conversation_load: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Number of conversations to load initially",
    )
    enable_virtualization: bool = Field(
        default=True, description="Use virtual scrolling for large lists"
    )

    # Input Behavior
    enable_multiline_input: bool = Field(
        default=True, description="Allow multi-line input with shift+enter"
    )
    input_syntax_highlighting: bool = Field(
        default=True, description="Syntax highlighting in input area"
    )

    # Mouse and Keyboard
    enable_mouse: bool = Field(default=True, description="Enable mouse interactions")
    vim_mode: bool = Field(default=False, description="Enable vim-style navigation")

    # Debug Settings
    debug: bool = Field(default=False, description="Enable debug logging")
    log_file: str | None = Field(
        default=None, description="Path to debug log file (None = textual.log)"
    )

    model_config = {"extra": "forbid"}  # Catch typos in config files
