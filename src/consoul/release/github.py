"""GitHub release creation using gh CLI."""

from __future__ import annotations

import subprocess


class GitHubError(Exception):
    """Raised when GitHub operations fail."""

    pass


def is_gh_cli_installed() -> bool:
    """Check if GitHub CLI (gh) is installed."""
    try:
        result = subprocess.run(
            ["gh", "--version"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def create_release(
    version: str, notes: str, target: str = "main", latest: bool = True
) -> str:
    """
    Create GitHub release using gh CLI.

    Args:
        version: Version tag (e.g., "v0.4.0")
        notes: Release notes markdown
        target: Target branch
        latest: Mark as latest release

    Returns:
        Release URL

    Raises:
        GitHubError: If release creation fails
    """
    if not is_gh_cli_installed():
        raise GitHubError("GitHub CLI (gh) is not installed")

    cmd = [
        "gh",
        "release",
        "create",
        version,
        "--title",
        f"Consoul {version}",
        "--notes",
        notes,
        "--target",
        target,
    ]

    if latest:
        cmd.append("--latest")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # gh outputs the release URL
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to create release: {e.stderr}") from e
