"""Pydantic configuration models for Consoul.

This module provides strongly-typed configuration models using Pydantic v2,
ensuring validation, type safety, and ease of use across the application.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_serializer,
    model_validator,
)


class Provider(str, Enum):
    """AI provider enumeration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class ModelConfig(BaseModel):
    """Configuration for AI model parameters.

    Supports multiple providers with provider-specific parameters.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
    )

    provider: Provider = Field(
        description="AI provider to use",
        examples=["openai", "anthropic", "google", "ollama"],
    )
    model: str = Field(
        description="Model name/ID",
        examples=[
            "gpt-4o",
            "claude-3-5-sonnet-20241022",
            "gemini-2.0-flash-exp",
            "llama3",
        ],
    )
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0)",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Maximum tokens to generate",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
    )
    top_k: int | None = Field(
        default=None,
        gt=0,
        description="Top-k sampling parameter (for some providers)",
    )
    frequency_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Frequency penalty (-2.0 to 2.0)",
    )
    presence_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Presence penalty (-2.0 to 2.0)",
    )
    stop_sequences: list[str] | None = Field(
        default=None,
        description="Stop sequences for generation",
    )

    @field_validator("model")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name is not empty."""
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_provider_params(self) -> ModelConfig:
        """Validate provider-specific parameters."""
        # Ollama typically doesn't use penalties
        if self.provider == Provider.OLLAMA and (
            self.frequency_penalty is not None or self.presence_penalty is not None
        ):
            raise ValueError(
                "Ollama provider does not support frequency_penalty or presence_penalty"
            )

        # Anthropic uses top_k, others typically don't
        if self.provider != Provider.ANTHROPIC and self.top_k is not None:
            raise ValueError(
                f"Provider {self.provider} does not support top_k parameter"
            )

        return self


class ConversationConfig(BaseModel):
    """Configuration for conversation management."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    save_history: bool = Field(
        default=True,
        description="Whether to save conversation history",
    )
    history_file: Path = Field(
        default=Path.home() / ".consoul" / "history.json",
        description="Path to history file",
    )
    max_history_length: int = Field(
        default=100,
        gt=0,
        description="Maximum number of messages to retain in history",
    )
    auto_save: bool = Field(
        default=True,
        description="Automatically save history after each message",
    )

    @field_validator("history_file", mode="before")
    @classmethod
    def expand_path(cls, v: Any) -> Path:
        """Expand user path and convert to Path object."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return Path(v) if not isinstance(v, Path) else v


class ContextConfig(BaseModel):
    """Configuration for context management."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    max_context_tokens: int = Field(
        default=4096,
        gt=0,
        description="Maximum number of tokens for context",
    )
    include_system_info: bool = Field(
        default=True,
        description="Include system information in context",
    )
    include_git_info: bool = Field(
        default=True,
        description="Include git repository information in context",
    )
    custom_context_files: list[Path] = Field(
        default_factory=list,
        description="Additional context files to include",
    )

    @field_validator("custom_context_files", mode="before")
    @classmethod
    def expand_paths(cls, v: Any) -> list[Path]:
        """Expand user paths and convert to Path objects."""
        if not v:
            return []
        if isinstance(v, (list, tuple)):
            return [Path(p).expanduser() if isinstance(p, str) else p for p in v]
        return []


class ProfileConfig(BaseModel):
    """Configuration profile with model, conversation, and context settings."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    name: str = Field(
        description="Profile name",
        examples=["default", "creative", "code-review", "fast"],
    )
    description: str = Field(
        description="Profile description",
    )
    model: ModelConfig = Field(
        description="Model configuration for this profile",
    )
    conversation: ConversationConfig = Field(
        default_factory=ConversationConfig,
        description="Conversation configuration",
    )
    context: ContextConfig = Field(
        default_factory=ContextConfig,
        description="Context configuration",
    )

    @field_validator("name")
    @classmethod
    def validate_profile_name(cls, v: str) -> str:
        """Validate profile name."""
        if not v or not v.strip():
            raise ValueError("Profile name cannot be empty")
        # Profile names should be valid identifiers
        if not v.replace("-", "_").replace("_", "").isalnum():
            raise ValueError(
                "Profile name must contain only alphanumeric characters, hyphens, or underscores"
            )
        return v.strip().lower()


class ConsoulConfig(BaseModel):
    """Root configuration for Consoul application.

    This is the main configuration model that contains all settings.
    """

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields for extensibility
        validate_assignment=True,
    )

    profiles: dict[str, ProfileConfig] = Field(
        description="Available configuration profiles",
    )
    active_profile: str = Field(
        default="default",
        description="Currently active profile name",
    )
    api_keys: dict[str, SecretStr] = Field(
        default_factory=dict,
        description="API keys for providers (runtime only, never serialized)",
    )
    global_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Global settings for extensibility",
    )

    @field_validator("active_profile")
    @classmethod
    def validate_active_profile(cls, v: str) -> str:
        """Validate active profile name is not empty."""
        if not v or not v.strip():
            raise ValueError("Active profile name cannot be empty")
        return v.strip().lower()

    @model_validator(mode="after")
    def validate_active_profile_exists(self) -> ConsoulConfig:
        """Validate that the active profile exists in profiles."""
        if self.active_profile not in self.profiles:
            raise ValueError(
                f"Active profile '{self.active_profile}' not found in profiles. "
                f"Available profiles: {', '.join(self.profiles.keys())}"
            )
        return self

    @model_serializer(mode="wrap", when_used="json")
    def serialize_model(self, serializer: Any) -> dict[str, Any]:
        """Custom serializer to exclude API keys from JSON output."""
        data: dict[str, Any] = serializer(self)
        # Remove api_keys from serialized output for security
        data.pop("api_keys", None)
        return data

    def get_active_profile(self) -> ProfileConfig:
        """Get the currently active profile configuration.

        Returns:
            The active ProfileConfig instance.

        Raises:
            KeyError: If the active profile doesn't exist.
        """
        return self.profiles[self.active_profile]
