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
    include_system_info: bool = True,
    include_git_info: bool = True,
) -> str:
    """Generate environment context for system prompt.

    Args:
        include_system_info: Include OS, shell, and working directory info
        include_git_info: Include git repository information

    Returns:
        Formatted context string with requested information.
        Returns empty string if both flags are False.

    Example:
        >>> context = get_environment_context(include_system_info=True)
        >>> "Working Directory:" in context
        True
    """
    sections = []

    if include_system_info:
        system_info = _get_system_info()
        if system_info:
            sections.append(system_info)

    if include_git_info:
        git_info = _get_git_info()
        if git_info:
            sections.append(git_info)

    return "\n\n".join(sections)


def _get_system_info() -> str:
    """Get system information section.

    Returns:
        Formatted system information including OS, shell, working directory,
        and current date/time.
    """
    try:
        # OS information
        os_name = platform.system()
        os_version = platform.release()

        # Platform-specific OS details
        if os_name == "Darwin":  # macOS
            try:
                # Get macOS version (e.g., "14.5.0" -> "macOS 14.5")
                mac_ver = platform.mac_ver()[0]
                if mac_ver:
                    major, minor = mac_ver.split(".")[:2]
                    os_display = f"macOS {major}.{minor} (Darwin {os_version})"
                else:
                    os_display = f"{os_name} {os_version}"
            except Exception:
                os_display = f"{os_name} {os_version}"
        elif os_name == "Linux":
            try:
                # Try to get Linux distribution info
                with open("/etc/os-release", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            distro = line.split("=")[1].strip().strip('"')
                            os_display = f"{distro} (Kernel {os_version})"
                            break
                    else:
                        os_display = f"{os_name} {os_version}"
            except Exception:
                os_display = f"{os_name} {os_version}"
        else:
            os_display = f"{os_name} {os_version}"

        # Shell information
        shell = os.environ.get("SHELL", "unknown")
        shell_name = Path(shell).name if shell != "unknown" else "unknown"

        # Working directory
        cwd = os.getcwd()

        # Current date/time
        now = datetime.now()
        # Try to get timezone abbreviation
        try:
            tz_name = now.astimezone().tzname()
        except Exception:
            tz_name = ""

        date_str = now.strftime("%Y-%m-%d %H:%M")
        if tz_name:
            date_str = f"{date_str} {tz_name}"

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
