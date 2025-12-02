"""Built-in configuration profiles for Consoul.

This module provides predefined profiles optimized for different use cases,
making it easy to switch between configurations for different tasks.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.config.models import ConsoulConfig


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


def list_available_profiles(config: ConsoulConfig) -> list[str]:
    """List all available profile names (built-in + custom).

    Args:
        config: ConsoulConfig instance to check for custom profiles.

    Returns:
        Sorted list of profile names.
    """
    builtin = set(get_builtin_profiles().keys())
    custom = set(config.profiles.keys())
    return sorted(builtin | custom)


def get_profile_description(profile_name: str, config: ConsoulConfig) -> str:
    """Get description for a profile.

    Args:
        profile_name: Name of the profile.
        config: ConsoulConfig instance to check for custom profiles.

    Returns:
        Profile description string.
    """
    # Check custom profiles first
    if profile_name in config.profiles:
        return config.profiles[profile_name].description

    # Fall back to built-in profiles
    builtin = get_builtin_profiles()
    if profile_name in builtin:
        desc = builtin[profile_name].get("description", "Unknown profile")
        assert isinstance(desc, str)  # Type guard for mypy
        return desc

    return "Unknown profile"
