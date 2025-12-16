"""Release management system for Consoul.

This module provides automated release workflows including:
- Semantic version detection and bumping
- Automated CHANGELOG generation from git commits
- Quality checks (tests, linting, type checking)
- Documentation publishing
- Git operations (merge, tag, push)
- GitHub release creation
- Gira ticket integration
"""

from __future__ import annotations

from consoul.release.manager import ReleaseManager, ReleaseResult
from consoul.release.version import VersionBump, determine_next_version, parse_version

__all__ = [
    "ReleaseManager",
    "ReleaseResult",
    "VersionBump",
    "determine_next_version",
    "parse_version",
]
