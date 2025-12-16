"""CHANGELOG generation from git commits."""

from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any


def get_commits_since_tag(tag: str | None = None) -> list[dict[str, Any]]:
    """
    Get commits since a specific tag with full details.

    Args:
        tag: Git tag to start from (None for all commits)

    Returns:
        List of commit dictionaries with hash, type, scope, message
    """
    if tag:
        cmd = [
            "git",
            "log",
            f"{tag}..HEAD",
            "--pretty=format:%H|||%s",
            "--no-merges",
        ]
    else:
        cmd = ["git", "log", "--pretty=format:%H|||%s", "--no-merges"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = []

        for line in result.stdout.split("\n"):
            if not line.strip():
                continue

            hash_part, message = line.split("|||", 1)

            # Parse conventional commit format
            match = re.match(r"^(\w+)(?:\(([^)]+)\))?:\s+(.+)", message)

            if match:
                commit_type, scope, msg = match.groups()
                commits.append(
                    {
                        "hash": hash_part[:7],
                        "type": commit_type,
                        "scope": scope,
                        "message": msg,
                        "raw": message,
                    }
                )
            else:
                # Non-conventional commit
                commits.append(
                    {
                        "hash": hash_part[:7],
                        "type": "other",
                        "scope": None,
                        "message": message,
                        "raw": message,
                    }
                )

        return commits

    except subprocess.CalledProcessError:
        return []


def categorize_commits(commits: list[dict[str, Any]]) -> dict[str, list[str]]:
    """
    Categorize commits into CHANGELOG sections.

    Args:
        commits: List of commit dictionaries

    Returns:
        Dictionary mapping category to list of formatted entries
    """
    categories: dict[str, list[str]] = {
        "Added": [],
        "Fixed": [],
        "Changed": [],
        "Deprecated": [],
        "Removed": [],
        "Security": [],
    }

    # Type to category mapping
    type_mapping = {
        "feat": "Added",
        "fix": "Fixed",
        "refactor": "Changed",
        "perf": "Changed",
        "chore": "Changed",
        "docs": "Changed",
        "test": "Changed",
        "build": "Changed",
        "ci": "Changed",
        "style": "Changed",
        "revert": "Changed",
    }

    for commit in commits:
        commit_type = commit["type"]
        scope = commit["scope"]
        message = commit["message"]
        commit_hash = commit["hash"]

        # Determine category
        category = type_mapping.get(commit_type)
        if not category:
            continue

        # Format entry
        if scope:
            entry = f"- **{scope}**: {message} ({commit_hash})"
        else:
            entry = f"- {message} ({commit_hash})"

        categories[category].append(entry)

    return categories


def generate_changelog_section(
    version: str,
    release_date: date | None = None,
    commits: list[dict[str, Any]] | None = None,
) -> str:
    """
    Generate CHANGELOG section for a version.

    Args:
        version: Version number (e.g., "0.4.0")
        release_date: Release date (defaults to today)
        commits: List of commits (auto-fetched if None)

    Returns:
        Formatted CHANGELOG section
    """
    if release_date is None:
        release_date = date.today()

    if commits is None:
        # Get last tag
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                check=False,
            )
            last_tag = result.stdout.strip() if result.returncode == 0 else None
        except subprocess.CalledProcessError:
            last_tag = None

        commits = get_commits_since_tag(last_tag)

    # Categorize commits
    categories = categorize_commits(commits)

    # Count commits by type for summary
    feat_count = sum(1 for c in commits if c["type"] == "feat")
    fix_count = sum(1 for c in commits if c["type"] == "fix")

    # Build section
    lines = [
        f"## [{version}] - {release_date.isoformat()}",
        "",
        f"**Stats:** {len(commits)} commits ({feat_count} features, {fix_count} fixes)",
        "",
    ]

    # Add non-empty categories
    for category, entries in categories.items():
        if entries:
            lines.append(f"### {category}")
            lines.append("")
            lines.extend(sorted(entries))  # Sort entries alphabetically
            lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def update_changelog(
    version: str, content: str, changelog_path: Path | None = None
) -> None:
    """
    Update CHANGELOG.md with new version section.

    Inserts new section after "## [Unreleased]" section.

    Args:
        version: Version number
        content: New changelog section content
        changelog_path: Path to CHANGELOG.md (defaults to ./CHANGELOG.md)
    """
    if changelog_path is None:
        changelog_path = Path("CHANGELOG.md")

    if not changelog_path.exists():
        # Create new changelog
        changelog_path.write_text(
            f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

{content}
""",
            encoding="utf-8",
        )
        return

    # Read existing changelog
    current_content = changelog_path.read_text(encoding="utf-8")

    # Find insertion point (after Unreleased section)
    unreleased_pattern = r"(## \[Unreleased\].*?)(\n---\n|\n## \[)"

    match = re.search(unreleased_pattern, current_content, re.DOTALL)

    if match:
        # Insert after Unreleased section
        before = current_content[: match.end(1)]
        after = current_content[match.start(2) :]

        new_content = f"{before}\n\n---\n\n{content}{after}"
    else:
        # No Unreleased section, insert at start after header
        header_end = current_content.find("\n## ")
        if header_end == -1:
            # No sections at all
            new_content = f"{current_content}\n{content}"
        else:
            before = current_content[:header_end]
            after = current_content[header_end:]
            new_content = f"{before}\n\n{content}{after}"

    changelog_path.write_text(new_content, encoding="utf-8")
