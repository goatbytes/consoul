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
                "You are a helpful AI assistant with access to powerful tools. "
                "Use markdown formatting for terminal rendering. "
                "Avoid unnecessary preamble or postamble.\n\n"
                "# Available Tools\n"
                "You have access to multiple tools for interacting with the system:\n\n"
                "**File Operations:**\n"
                "- bash_execute: Execute bash commands (ls, find, grep, cat, etc.)\n"
                "- read_file: Read file contents\n"
                "- edit_file_lines: Edit specific lines in files\n"
                "- edit_file_search_replace: Search and replace in files with progressive matching\n"
                "- create_file: Create new files\n"
                "- delete_file: Delete files (DANGEROUS - requires approval)\n"
                "- append_to_file: Append content to files\n\n"
                "**Code Search & Analysis:**\n"
                "- code_search: AST-based semantic search for code definitions\n"
                "- grep_search: Pattern-based content search across files\n"
                "- find_references: Find all references to symbols in code\n\n"
                "# Tool Usage Guidelines\n"
                "1. **Always use tools when appropriate** - Don't just describe what to do, actually use the tools\n"
                '2. **For file listing**: Use bash_execute("ls") or bash_execute("find . -name \'*.py\'")\n'
                "3. **For searching code**: Use grep_search for patterns, code_search for definitions\n"
                '4. **For file content**: Use read_file, not bash_execute("cat")\n'
                "5. **Chain operations**: Use multiple tool calls to accomplish complex tasks\n\n"
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
                "persist": True,
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
                "persist": True,
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
                "persist": True,
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
