"""Version detection and semantic versioning logic."""

from __future__ import annotations

import re
import subprocess
from enum import Enum
from typing import NamedTuple


class VersionBump(str, Enum):
    """Type of version bump to perform."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    AUTO = "auto"


class Version(NamedTuple):
    """Semantic version components."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        """Return version string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def bump(self, bump_type: VersionBump) -> Version:
        """Return new version with specified bump applied."""
        if bump_type == VersionBump.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif bump_type == VersionBump.MINOR:
            return Version(self.major, self.minor + 1, 0)
        else:  # PATCH
            return Version(self.major, self.minor, self.patch + 1)


def parse_version(version_str: str) -> Version:
    """
    Parse semantic version string.

    Args:
        version_str: Version string like "0.4.0" or "v0.4.0"

    Returns:
        Version tuple

    Raises:
        ValueError: If version string is invalid
    """
    # Remove 'v' prefix if present
    clean = version_str.lstrip("v")

    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", clean)
    if not match:
        raise ValueError(f"Invalid version string: {version_str}")

    major, minor, patch = map(int, match.groups())
    return Version(major, minor, patch)


def get_current_version() -> Version:
    """
    Get current version from pyproject.toml.

    Returns:
        Current version

    Raises:
        FileNotFoundError: If pyproject.toml not found
        ValueError: If version cannot be parsed
    """
    try:
        with open("pyproject.toml") as f:
            for line in f:
                if line.startswith("version = "):
                    # Extract version from: version = "0.4.0"
                    match = re.search(r'version\s*=\s*"([^"]+)"', line)
                    if match:
                        return parse_version(match.group(1))
    except FileNotFoundError as e:
        raise FileNotFoundError("pyproject.toml not found in current directory") from e

    raise ValueError("Could not find version in pyproject.toml")


def get_commits_since_last_tag() -> list[str]:
    """
    Get all commits since the last git tag.

    Returns:
        List of commit messages in format "type(scope): message"
    """
    try:
        # Get last tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            last_tag = result.stdout.strip()
            # Get commits since tag
            result = subprocess.run(
                ["git", "log", f"{last_tag}..HEAD", "--pretty=format:%s"],
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            # No tags yet, get all commits
            result = subprocess.run(
                ["git", "log", "--pretty=format:%s"],
                capture_output=True,
                text=True,
                check=True,
            )

        return [line for line in result.stdout.split("\n") if line.strip()]

    except subprocess.CalledProcessError:
        return []


def analyze_commits(commits: list[str]) -> VersionBump:
    """
    Analyze commits to determine appropriate version bump.

    Uses Conventional Commits standard:
    - BREAKING CHANGE or ! after type: major bump
    - feat: minor bump
    - fix, chore, docs, etc.: patch bump

    Args:
        commits: List of commit messages

    Returns:
        Recommended version bump type
    """
    has_breaking = False
    has_feat = False
    has_fix = False

    for commit in commits:
        # Check for breaking change indicators
        if "BREAKING CHANGE" in commit or "!" in commit.split(":")[0]:
            has_breaking = True
            continue

        # Parse conventional commit format: type(scope): message
        match = re.match(r"^(\w+)(?:\([^)]+\))?:", commit)
        if match:
            commit_type = match.group(1)

            if commit_type == "feat":
                has_feat = True
            elif commit_type == "fix":
                has_fix = True

    # Determine bump type based on commits
    if has_breaking:
        return VersionBump.MAJOR
    elif has_feat:
        return VersionBump.MINOR
    elif has_fix:
        return VersionBump.PATCH
    else:
        # Default to patch for any other changes
        return VersionBump.PATCH


def determine_next_version(
    current: Version | None = None, bump_type: VersionBump = VersionBump.AUTO
) -> tuple[Version, VersionBump]:
    """
    Determine the next version number.

    Args:
        current: Current version (auto-detected if None)
        bump_type: Type of bump (auto-detected if AUTO)

    Returns:
        Tuple of (next_version, bump_type_used)
    """
    if current is None:
        current = get_current_version()

    if bump_type == VersionBump.AUTO:
        commits = get_commits_since_last_tag()
        bump_type = analyze_commits(commits)

    next_version = current.bump(bump_type)

    return next_version, bump_type
