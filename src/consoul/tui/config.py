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

    # Auto-title Generation
    auto_generate_titles: bool = Field(
        default=True,
        description="Auto-generate conversation titles using LLM",
    )
    auto_title_provider: str | None = Field(
        default=None,
        description="Provider for title generation (openai, anthropic, google, ollama, or None for auto-detect)",
    )
    auto_title_model: str | None = Field(
        default=None,
        description="Model for title generation (None = use provider default)",
    )
    auto_title_api_key: str | None = Field(
        default=None,
        description="API key for title generation (None = use from env/config)",
    )
    auto_title_prompt: str = Field(
        default="Generate a concise 2-8 word title for this conversation. Based on:\n\nUser: {user_message}\n\nAssistant: {assistant_message}\n\nReturn only the title with no quotes or extra text.",
        description="Prompt template for title generation",
    )
    auto_title_max_tokens: int = Field(
        default=20, ge=5, le=100, description="Max tokens for generated title"
    )
    auto_title_temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Temperature for title generation"
    )

    model_config = {"extra": "forbid"}  # Catch typos in config files
