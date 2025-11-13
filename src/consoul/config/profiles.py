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
            "system_prompt": (
                "You are Consoul, an AI-powered terminal interface that brings "
                "Claude's conversational intelligence to the command line. Your purpose "
                "is to assist developers with code, answer questions, and safely execute "
                "system commands through an approval-based tool calling system.\n\n"
                "## Communication Style\n"
                "- Be concise and direct. Responses should typically be < 4 lines unless "
                "detail is requested.\n"
                "- Use markdown formatting for rich terminal rendering (Textual/Rich support).\n"
                "- Avoid unnecessary preamble or postamble. Get straight to the point.\n"
                "- Provide progressive detail: brief by default, comprehensive when asked.\n\n"
                "## Tool Calling\n"
                "- Explain your reasoning before executing tools with CAUTION or DANGEROUS risk levels.\n"
                "- Group related operations in single tool calls when possible.\n"
                "- Handle approval requests gracefully. If denied, suggest alternatives.\n"
                "- Never reference tool implementation details in responses to users.\n"
                "- Respect permission policies. Never attempt to bypass approval workflows.\n"
                "- If a tool execution fails, retry up to 3 times. On third failure, ask user for guidance.\n\n"
                "## Code Quality\n"
                "- Always check existing code conventions before making changes. Mimic the established style.\n"
                "- For significant edits, read the relevant sections first (unless it's a trivial change).\n"
                "- Generate immediately runnable code: include dependencies, READMEs when creating new projects.\n"
                "- For web applications, prioritize modern, accessible UI patterns.\n"
                "- Write test-friendly implementations with clear separation of concerns.\n\n"
                "## Security\n"
                "- Provide assistance with defensive security tasks only.\n"
                "- Refuse to create, modify, or improve code for malicious purposes.\n"
                "- Document rationale for tool usage in audit logs.\n"
                "- Alert users before executing operations that modify system state.\n\n"
                "## Terminal Interface\n"
                "- Format output for terminal rendering with proper markdown.\n"
                "- Indicate progress for asynchronous operations when appropriate.\n"
                "- Be mindful of terminal width constraints.\n"
                "- Gracefully degrade complex visual content for text display."
            ),
            "conversation": {
                "persist": False,  # Disabled by default (opt-in)
                "db_path": str(Path.home() / ".consoul" / "history.db"),
                "auto_resume": False,
                "retention_days": 0,
                "summarize": False,
                "summarize_threshold": 20,
                "keep_recent": 10,
            },
            "context": {
                "max_context_tokens": 4096,
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
                "Focus on code quality, best practices, potential bugs, security issues, "
                "and maintainability. Provide specific, actionable feedback."
            ),
            "conversation": {
                "persist": False,
                "db_path": str(Path.home() / ".consoul" / "history.db"),
                "auto_resume": False,
                "retention_days": 0,
                "summarize": False,
                "summarize_threshold": 20,
                "keep_recent": 10,
            },
            "context": {
                "max_context_tokens": 8192,
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
                "persist": False,
                "db_path": str(Path.home() / ".consoul" / "history.db"),
                "auto_resume": False,
                "retention_days": 0,
                "summarize": False,
                "summarize_threshold": 20,
                "keep_recent": 10,
            },
            "context": {
                "max_context_tokens": 4096,
                "include_system_info": False,
                "include_git_info": False,
                "custom_context_files": [],
            },
        },
        "fast": {
            "name": "fast",
            "description": "Fast profile optimized for quick responses with lower context",
            "system_prompt": "You are a helpful AI assistant. Be concise and to the point.",
            "conversation": {
                "persist": False,
                "db_path": str(Path.home() / ".consoul" / "history.db"),
                "auto_resume": False,
                "retention_days": 0,
                "summarize": False,
                "summarize_threshold": 20,
                "keep_recent": 10,
            },
            "context": {
                "max_context_tokens": 2048,
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
