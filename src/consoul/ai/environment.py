"""Environment context generation for AI conversations.

This module provides functionality to gather and format system and git repository
information to be injected into AI system prompts, giving models better context
about the user's working environment.
"""

from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path


def get_environment_context(
    include_os: bool = False,
    include_shell: bool = False,
    include_directory: bool = False,
    include_datetime: bool = False,
    include_git: bool = False,
    # Legacy parameters for backward compatibility
    include_system_info: bool | None = None,
    include_git_info: bool | None = None,
) -> str:
    """Generate environment context for system prompt with granular control.

    Args:
        include_os: Include OS/platform information
        include_shell: Include shell type
        include_directory: Include working directory
        include_datetime: Include current date/time
        include_git: Include git repository information
        include_system_info: DEPRECATED - Use granular flags instead.
                           If True, enables all system flags (os, shell, directory, datetime).
                           If False, disables all system flags.
        include_git_info: DEPRECATED - Use include_git instead.

    Returns:
        Formatted context string with requested information.
        Returns empty string if all flags are False.

    Example - Granular control:
        >>> context = get_environment_context(include_os=True, include_datetime=True)
        >>> "OS:" in context
        True
        >>> "Working Directory:" not in context
        True

    Example - Legacy compatibility:
        >>> context = get_environment_context(include_system_info=True)
        >>> "Working Directory:" in context
        True
    """
    # Handle legacy parameters for backward compatibility
    if include_system_info is not None:
        if include_system_info:
            # Enable all granular system flags
            include_os = True
            include_shell = True
            include_directory = True
            include_datetime = True
        else:
            # Disable all granular system flags
            include_os = False
            include_shell = False
            include_directory = False
            include_datetime = False

    if include_git_info is not None:
        include_git = include_git_info

    sections = []

    # Build environment section if any system flags are enabled
    if include_os or include_shell or include_directory or include_datetime:
        env_parts = []

        if include_os:
            os_info = _get_os_info()
            if os_info:
                env_parts.append(f"- OS: {os_info}")

        if include_shell:
            shell_info = _get_shell_info()
            if shell_info:
                env_parts.append(f"- Shell: {shell_info}")

        if include_directory:
            dir_info = _get_directory_info()
            if dir_info:
                env_parts.append(f"- Working Directory: {dir_info}")

        if include_datetime:
            datetime_info = _get_datetime_info()
            if datetime_info:
                env_parts.append(f"- Date: {datetime_info}")

        if env_parts:
            sections.append("## Environment\n" + "\n".join(env_parts))

    # Add git information if requested
    if include_git:
        git_info = _get_git_info()
        if git_info:
            sections.append(git_info)

    return "\n\n".join(sections)


def _get_os_info() -> str:
    """Get OS/platform information.

    Returns:
        Formatted OS information (e.g., "macOS 15.2 (Darwin 24.6.0)")
    """
    try:
        os_name = platform.system()
        os_version = platform.release()

        # Platform-specific OS details
        if os_name == "Darwin":  # macOS
            try:
                # Get macOS version (e.g., "14.5.0" -> "macOS 14.5")
                mac_ver = platform.mac_ver()[0]
                if mac_ver:
                    major, minor = mac_ver.split(".")[:2]
                    return f"macOS {major}.{minor} (Darwin {os_version})"
                else:
                    return f"{os_name} {os_version}"
            except Exception:
                return f"{os_name} {os_version}"
        elif os_name == "Linux":
            try:
                # Try to get Linux distribution info
                with open("/etc/os-release", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            distro = line.split("=")[1].strip().strip('"')
                            return f"{distro} (Kernel {os_version})"
                    else:
                        return f"{os_name} {os_version}"
            except Exception:
                return f"{os_name} {os_version}"
        else:
            return f"{os_name} {os_version}"
    except Exception:
        return ""


def _get_shell_info() -> str:
    """Get shell type.

    Returns:
        Shell name (e.g., "zsh", "bash")
    """
    try:
        shell = os.environ.get("SHELL", "unknown")
        return Path(shell).name if shell != "unknown" else "unknown"
    except Exception:
        return ""


def _get_directory_info() -> str:
    """Get current working directory.

    Returns:
        Absolute path to current working directory
    """
    try:
        return os.getcwd()
    except Exception:
        return ""


def _get_datetime_info() -> str:
    """Get current date/time with timezone.

    Returns:
        Formatted date/time string (e.g., "2025-12-16 20:30 PST")
    """
    try:
        now = datetime.now()
        # Try to get timezone abbreviation
        try:
            tz_name = now.astimezone().tzname()
        except Exception:
            tz_name = ""

        date_str = now.strftime("%Y-%m-%d %H:%M")
        if tz_name:
            date_str = f"{date_str} {tz_name}"
        return date_str
    except Exception:
        return ""


def _get_system_info() -> str:
    """Get system information section.

    DEPRECATED: Use get_environment_context() with granular flags instead.

    Returns:
        Formatted system information including OS, shell, working directory,
        and current date/time.
    """
    try:
        os_display = _get_os_info()
        shell_name = _get_shell_info()
        cwd = _get_directory_info()
        date_str = _get_datetime_info()

        return f"""## Environment
- OS: {os_display}
- Shell: {shell_name}
- Working Directory: {cwd}
- Date: {date_str}"""

    except Exception:
        # If we fail to get system info, return empty string
        # to avoid breaking the conversation
        return ""


def _get_git_info() -> str:
    """Get git repository information.

    Returns:
        Formatted git repository information including branch, status,
        remote, and last commit. Returns empty string if not in a git repo.
    """
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )

        if result.returncode != 0:
            # Not in a git repository
            return ""

        info_lines = []

        # Get repository root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            repo_root = result.stdout.strip()
            repo_name = Path(repo_root).name
            info_lines.append(f"- Repository: {repo_name}")

        # Get current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch:
                info_lines.append(f"- Branch: {branch}")
            else:
                # Detached HEAD - get commit hash
                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                if result.returncode == 0:
                    commit = result.stdout.strip()
                    info_lines.append(f"- Branch: detached HEAD at {commit}")

        # Get repository status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            status_output = result.stdout.strip()
            if status_output:
                # Count modified files
                lines = status_output.split("\n")
                modified_count = len(lines)
                info_lines.append(f"- Status: {modified_count} file(s) modified")
            else:
                info_lines.append("- Status: clean")

        # Get remote information
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            # Clean up SSH URLs for display
            if remote_url.startswith("git@"):
                # git@github.com:user/repo.git -> github.com/user/repo
                remote_url = remote_url.replace(":", "/").replace("git@", "")
            if remote_url.endswith(".git"):
                remote_url = remote_url[:-4]
            info_lines.append(f"- Remote: {remote_url}")

        # Get last commit
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%h - %s"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            last_commit = result.stdout.strip()
            if last_commit:
                info_lines.append(f"- Last Commit: {last_commit}")

        # Only return git info if we got at least some information
        if info_lines:
            return "## Git Repository\n" + "\n".join(info_lines)

        return ""

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # Git not available or timeout - silently return empty string
        return ""
