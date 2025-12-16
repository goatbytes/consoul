"""Security utilities for API key handling and .env file management.

This module provides utilities to ensure API keys are handled securely
and .env files are properly gitignored.
"""

from __future__ import annotations

import sys
from pathlib import Path


def check_env_file_in_gitignore(project_root: Path | None = None) -> bool:
    """Check if .env file is in .gitignore.

    Args:
        project_root: Optional path to project root. If None, uses current directory.

    Returns:
        True if .env is in .gitignore, False otherwise.
    """
    if project_root is None:
        project_root = Path.cwd()

    gitignore_path = project_root / ".gitignore"
    if not gitignore_path.exists():
        return False

    try:
        content = gitignore_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Check for .env entries
        for line in lines:
            # Strip comments and whitespace
            line = line.split("#")[0].strip()
            if line in (".env", ".env.local", "*.env", ".env*"):
                return True

        return False
    except OSError:
        return False


def warn_if_env_not_ignored(project_root: Path | None = None) -> None:
    """Print warning if .env file exists but not in .gitignore.

    Args:
        project_root: Optional path to project root. If None, uses current directory.
    """
    if project_root is None:
        project_root = Path.cwd()

    env_file = project_root / ".env"
    if not env_file.exists():
        # No .env file, no warning needed
        return

    if not check_env_file_in_gitignore(project_root):
        print(
            "⚠️  WARNING: .env file found but not in .gitignore!\n"
            "   This may expose sensitive API keys if committed to version control.\n"
            "   Add '.env' to your .gitignore file to prevent accidental commits.",
            file=sys.stderr,
        )


def mask_api_key(key: str, show_chars: int = 4) -> str:
    """Mask API key for safe display.

    Shows only the first and last N characters, masking the rest.

    Args:
        key: The API key to mask.
        show_chars: Number of characters to show at start and end (default: 4).

    Returns:
        Masked API key string.

    Examples:
        >>> mask_api_key("sk-ant-1234567890abcdef")
        'sk-a...cdef'
        >>> mask_api_key("short")
        '****'
    """
    if not key:
        return ""

    key_len = len(key)
    if key_len <= show_chars * 2:
        # Key too short, just mask it completely
        return "*" * min(key_len, 4)

    # Show first and last show_chars characters
    start = key[:show_chars]
    end = key[-show_chars:]
    return f"{start}...{end}"
