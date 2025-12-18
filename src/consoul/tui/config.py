"""TUI-specific configuration models.

This module defines Pydantic configuration models for Consoul's Textual TUI,
covering appearance, performance tuning, and behavior settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from consoul.config.models import ConsoulCoreConfig  # noqa: TC001

if TYPE_CHECKING:
    from consoul.tui.profiles import ProfileConfig

__all__ = ["ConsoulTuiConfig", "TuiConfig"]


class TuiConfig(BaseModel):
    """TUI-specific configuration.

    Controls appearance, behavior, and performance of the Textual TUI.
    These settings are independent of core AI configuration.
    """

    # Theme and Appearance
    theme: str = Field(default="consoul-dark", description="TUI color theme")
    show_sidebar: bool = Field(
        default=True, description="Show conversation list sidebar"
    )
    sidebar_width: str = Field(default="20%", description="Sidebar width (CSS units)")
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

    # Loading Screen
    show_loading_screen: bool = Field(
        default=True, description="Show animated loading screen on startup"
    )
    loading_animation_style: Literal[
        "sound_wave", "matrix_rain", "binary_wave", "code_stream", "pulse"
    ] = Field(default="sound_wave", description="Animation style for loading screen")
    loading_show_progress: bool = Field(
        default=True, description="Show progress bar on loading screen"
    )

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


class ConsoulTuiConfig(BaseModel):
    """Complete TUI configuration with profiles + core SDK settings + TUI settings.

    This is the configuration model for TUI applications, containing:
    - profiles: dict[str, ProfileConfig] (TUI-specific profile management)
    - active_profile: str (currently active profile name)
    - core: ConsoulCoreConfig (profile-free SDK settings)
    - tui: TuiConfig (TUI-specific appearance/behavior)

    TUI applications use profiles for workflow management, while the SDK
    operates profile-free with explicit parameters.
    """

    # Profile fields (TUI-specific, not in ConsoulCoreConfig)
    profiles: dict[str, ProfileConfig] = Field(
        description="Available configuration profiles (TUI feature)",
    )
    active_profile: str = Field(
        default="default",
        description="Currently active profile name",
    )

    # Core SDK config and TUI config
    core: ConsoulCoreConfig
    tui: TuiConfig = Field(default_factory=TuiConfig)

    model_config = {"extra": "forbid"}

    @field_validator("active_profile")
    @classmethod
    def validate_active_profile(cls, v: str) -> str:
        """Validate active profile name is not empty."""
        if not v or not v.strip():
            raise ValueError("Active profile name cannot be empty")
        return v.strip().lower()

    @model_validator(mode="after")
    def validate_active_profile_exists(self) -> ConsoulTuiConfig:
        """Validate that the active profile exists in profiles."""
        if self.active_profile not in self.profiles:
            raise ValueError(
                f"Active profile '{self.active_profile}' not found in profiles. "
                f"Available profiles: {', '.join(self.profiles.keys())}"
            )
        return self

    @property
    def current_provider(self):  # type: ignore[no-untyped-def]
        """Access core.current_provider."""
        return self.core.current_provider

    @property
    def current_model(self) -> str:
        """Access core.current_model."""
        return self.core.current_model

    @property
    def tools(self):  # type: ignore[no-untyped-def]
        """Access core.tools."""
        return self.core.tools

    @property
    def show_thinking(self):  # type: ignore[no-untyped-def]
        """Access core.show_thinking."""
        return self.core.show_thinking

    @property
    def thinking_models(self):  # type: ignore[no-untyped-def]
        """Access core.thinking_models."""
        return self.core.thinking_models

    @property
    def provider_configs(self):  # type: ignore[no-untyped-def]
        """Access core.provider_configs."""
        return self.core.provider_configs

    @property
    def tool_presets(self):  # type: ignore[no-untyped-def]
        """Access core.tool_presets."""
        return self.core.tool_presets

    def get_active_profile(self) -> ProfileConfig:
        """Get the currently active profile configuration.

        Returns:
            The active ProfileConfig instance.

        Raises:
            KeyError: If the active profile doesn't exist.
        """
        return self.profiles[self.active_profile]

    def get_current_model_config(self):  # type: ignore[no-untyped-def]
        """Delegate to core.get_current_model_config()."""
        return self.core.get_current_model_config()

    def get_api_key(self, provider):  # type: ignore[no-untyped-def]
        """Delegate to core.get_api_key()."""
        return self.core.get_api_key(provider)
