"""Pydantic configuration models for Consoul.

This module provides strongly-typed configuration models using Pydantic v2,
ensuring validation, type safety, and ease of use across the application.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_serializer,
    model_validator,
)

if TYPE_CHECKING:
    from consoul.config.env import EnvSettings
else:
    EnvSettings = Any  # type: ignore[misc,assignment]


class Provider(str, Enum):
    """AI provider enumeration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class BaseModelConfig(BaseModel):
    """Base configuration for AI model parameters shared across all providers."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    model: str = Field(
        description="Model name/ID",
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


class OpenAIModelConfig(BaseModelConfig):
    """OpenAI-specific model configuration."""

    provider: Literal[Provider.OPENAI] = Provider.OPENAI
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
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
    seed: int | None = Field(
        default=None,
        description="Seed for deterministic sampling (beta feature)",
    )
    logit_bias: dict[str, float] | None = Field(
        default=None,
        description="Modify likelihood of specific tokens appearing",
    )
    response_format: dict[str, Any] | None = Field(
        default=None,
        description="Response format (e.g., {'type': 'json_object'} or {'type': 'json_schema', 'json_schema': {...}})",
    )


class AnthropicModelConfig(BaseModelConfig):
    """Anthropic-specific model configuration."""

    provider: Literal[Provider.ANTHROPIC] = Provider.ANTHROPIC
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
    )
    top_k: int | None = Field(
        default=None,
        gt=0,
        description="Top-k sampling parameter (Anthropic-specific)",
    )


class GoogleModelConfig(BaseModelConfig):
    """Google Gemini-specific model configuration."""

    provider: Literal[Provider.GOOGLE] = Provider.GOOGLE
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
    )
    top_k: int | None = Field(
        default=None,
        gt=0,
        description="Top-k sampling parameter",
    )


class OllamaModelConfig(BaseModelConfig):
    """Ollama-specific model configuration for local models."""

    provider: Literal[Provider.OLLAMA] = Provider.OLLAMA
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
    )
    top_k: int | None = Field(
        default=None,
        gt=0,
        description="Top-k sampling parameter",
    )


# Type alias for discriminated union of all model configs
ModelConfigUnion = Annotated[
    OpenAIModelConfig | AnthropicModelConfig | GoogleModelConfig | OllamaModelConfig,
    Field(discriminator="provider"),
]

# For backward compatibility in tests and simpler usage
ModelConfig = ModelConfigUnion


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
        """Expand user paths and convert to Path objects.

        Accepts:
        - List or tuple of strings/Paths
        - Single string (converted to single-item list)
        - Single Path (converted to single-item list)
        - None or empty (returns empty list)
        """
        if not v:
            return []
        # Handle single string or Path
        if isinstance(v, (str, Path)):
            path = Path(v).expanduser() if isinstance(v, str) else v.expanduser()
            return [path]
        # Handle list/tuple
        if isinstance(v, (list, tuple)):
            return [Path(p).expanduser() if isinstance(p, str) else p for p in v]
        # Invalid type
        raise ValueError(
            f"custom_context_files must be a string, Path, or list/tuple of strings/Paths, "
            f"got {type(v).__name__}"
        )


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
        extra="forbid",  # Reject unknown fields to catch typos and enforce schema
        validate_assignment=True,
        arbitrary_types_allowed=True,  # Allow EnvSettings type
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
    env_settings: EnvSettings | None = Field(
        default=None,
        exclude=True,
        description="Environment settings for lazy API key loading",
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

    @model_serializer(mode="wrap")
    def serialize_model(self, serializer: Any) -> dict[str, Any]:
        """Custom serializer to exclude API keys from all serialization modes.

        This ensures API keys are never leaked via model_dump(), YAML export,
        or any other serialization path.
        """
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

    def get_api_key(self, provider: Provider) -> SecretStr | None:
        """Get API key for a provider with lazy loading from environment.

        Args:
            provider: The provider to get the API key for.

        Returns:
            SecretStr containing the API key, or None if not found.
        """
        from consoul.config.env import EnvSettings as RealEnvSettings
        from consoul.config.env import get_api_key

        return get_api_key(
            provider,
            self.env_settings
            if isinstance(self.env_settings, RealEnvSettings)
            else None,
        )
