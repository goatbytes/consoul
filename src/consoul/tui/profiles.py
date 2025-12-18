"""TUI-specific profile configuration.

This module contains ProfileConfig and builtin profiles, extracted from SDK core
to decouple profiles from the SDK layer. Profiles are a TUI/CLI convenience feature
for workflow management, not a core SDK requirement.

Moved from: consoul.config.models.ProfileConfig
Moved from: consoul.config.profiles.get_builtin_profiles()
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from consoul.config.models import (
        ContextConfig,
        ConversationConfig,
        ModelConfigUnion,
    )


# Import at runtime to avoid circular dependency
# These are only used for type hints and runtime validation
def _get_model_imports() -> tuple[type, type, type]:
    """Lazy import of model config types to avoid circular dependencies."""
    from consoul.config.models import (
        ContextConfig,
        ConversationConfig,
        ModelConfigUnion,
    )

    return ContextConfig, ConversationConfig, ModelConfigUnion  # type: ignore[return-value]


class ProfileConfig(BaseModel):
    """Configuration profile with conversation and context settings.

    Profiles define HOW to use AI (system prompts, context, conversation settings),
    including WHICH AI model to use.

    NOTE: This is a TUI/CLI feature. SDK users should use explicit parameters
    (model, system_prompt, temperature, etc.) instead of profiles.
    """

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
    system_prompt: str | None = Field(
        default=None,
        description="Custom system prompt for this profile",
    )
    model: ModelConfigUnion | None = Field(
        default=None,
        description="Model configuration for this profile (optional, can be specified at runtime)",
    )
    conversation: ConversationConfig = Field(
        default_factory=lambda: _get_model_imports()[1](),
        description="Conversation configuration",
    )
    context: ContextConfig = Field(
        default_factory=lambda: _get_model_imports()[0](),
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


def get_builtin_profiles() -> dict[str, dict[str, Any]]:
    """Get all built-in configuration profiles.

    Profiles define HOW to use AI (system prompts, context settings),
    not WHICH AI to use (model/provider are configured separately).

    Returns:
        Dictionary mapping profile names to their configuration dictionaries.
    """
    return {
        "default": {
            "name": "default",
            "description": "Default profile with balanced settings for general use",
            # NOTE: Environment context (OS, working directory, git info) is automatically
            # prepended to this prompt when include_system_info or include_git_info are enabled.
            # {AVAILABLE_TOOLS} marker will be replaced at runtime with dynamic tool documentation.
            "system_prompt": (
                "You are a helpful AI assistant with access to powerful tools. "
                "The environment information above provides details about the user's "
                "working directory, git repository, and system. Use this context "
                "to provide more relevant and accurate assistance.\n\n"
                "Use markdown formatting for terminal rendering. "
                "Avoid unnecessary preamble or postamble.\n\n"
                "{AVAILABLE_TOOLS}\n\n"
                "# Code Guidelines\n"
                "When writing code, check existing conventions first and mimic the established style. "
                "Generate immediately runnable code with dependencies included.\n\n"
                "# Security\n"
                "Provide assistance with defensive security tasks only."
            ),
            "model": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 1.0,
            },
            "conversation": {
                "persist": True,
                "db_path": str(Path.home() / ".consoul" / "history.db"),
                "auto_resume": False,
                "retention_days": 0,
                "summarize": False,
                "summarize_threshold": 20,
                "keep_recent": 10,
            },
            "context": {
                "max_context_tokens": 0,  # Auto-size: 75% of model's context window
                "include_system_info": True,
                "include_git_info": True,
                "custom_context_files": [],
            },
        },
        "code-review": {
            "name": "code-review",
            "description": "Focused profile for thorough code review",
            "system_prompt": (
                "You are a senior software engineer conducting a thorough code review. "
                "Use the environment information above to understand the project context, "
                "including the repository, current branch, and working directory.\n\n"
                "Focus on code quality, best practices, potential bugs, security issues, "
                "and maintainability. Provide specific, actionable feedback.\n\n"
                "{AVAILABLE_TOOLS}"
            ),
            "model": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.3,
            },
            "conversation": {
                "persist": True,
                "db_path": str(Path.home() / ".consoul" / "history.db"),
                "auto_resume": False,
                "retention_days": 0,
                "summarize": False,
                "summarize_threshold": 20,
                "keep_recent": 10,
            },
            "context": {
                "max_context_tokens": 0,  # Auto-size: 75% of model's context window
                "include_system_info": True,
                "include_git_info": True,
                "custom_context_files": [],
            },
        },
        "creative": {
            "name": "creative",
            "description": "Creative profile for brainstorming and ideation",
            "system_prompt": (
                "You are a creative AI assistant focused on innovative ideas and "
                "brainstorming. Think outside the box, explore unconventional solutions, "
                "and encourage creative thinking."
            ),
            "model": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 1.5,
            },
            "conversation": {
                "persist": True,
                "db_path": str(Path.home() / ".consoul" / "history.db"),
                "auto_resume": False,
                "retention_days": 0,
                "summarize": False,
                "summarize_threshold": 20,
                "keep_recent": 10,
            },
            "context": {
                "max_context_tokens": 0,  # Auto-size: 75% of model's context window
                "include_system_info": False,
                "include_git_info": False,
                "custom_context_files": [],
            },
        },
        "fast": {
            "name": "fast",
            "description": "Fast profile optimized for quick responses with lower context",
            "system_prompt": (
                "You are a helpful AI assistant. Be concise and to the point.\n\n"
                "{AVAILABLE_TOOLS}"
            ),
            "model": {
                "provider": "anthropic",
                "model": "claude-3-5-haiku-20241022",
                "temperature": 1.0,
            },
            "conversation": {
                "persist": True,
                "db_path": str(Path.home() / ".consoul" / "history.db"),
                "auto_resume": False,
                "retention_days": 0,
                "summarize": False,
                "summarize_threshold": 20,
                "keep_recent": 10,
            },
            "context": {
                "max_context_tokens": 4096,  # Explicit cap for speed
                "include_system_info": True,
                "include_git_info": True,
                "custom_context_files": [],
            },
        },
    }


def list_available_profiles(profiles: dict[str, ProfileConfig]) -> list[str]:
    """List all available profile names (built-in + custom).

    Args:
        profiles: Dictionary of custom profiles from TUI config.

    Returns:
        Sorted list of profile names.
    """
    builtin = set(get_builtin_profiles().keys())
    custom = set(profiles.keys())
    return sorted(builtin | custom)


def get_profile_description(
    profile_name: str, profiles: dict[str, ProfileConfig]
) -> str:
    """Get description for a profile.

    Args:
        profile_name: Name of the profile.
        profiles: Dictionary of custom profiles from TUI config.

    Returns:
        Profile description string.
    """
    # Check custom profiles first
    if profile_name in profiles:
        return profiles[profile_name].description

    # Fall back to built-in profiles
    builtin = get_builtin_profiles()
    if profile_name in builtin:
        desc = builtin[profile_name].get("description", "Unknown profile")
        assert isinstance(desc, str)  # Type guard for mypy
        return desc

    return "Unknown profile"


__all__ = [
    "ProfileConfig",
    "get_builtin_profiles",
    "get_profile_description",
    "list_available_profiles",
]
