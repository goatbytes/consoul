"""Whitelist management for bash commands.

Provides command whitelisting with exact matches and regex patterns,
allowing trusted commands to bypass approval prompts while maintaining
blocklist protection.

This is a security-sensitive module. Whitelisted commands bypass normal
approval workflows, so patterns should be carefully reviewed.

Example:
    >>> from consoul.ai.tools.permissions.whitelist import WhitelistManager
    >>> manager = WhitelistManager()
    >>> manager.add_pattern("git status")  # Exact match
    >>> manager.add_pattern("git.*")  # Regex pattern
    >>> manager.is_whitelisted("git status")  # True
    >>> manager.is_whitelisted("git log")  # True (matches git.*)
    >>> manager.is_whitelisted("rm -rf /")  # False
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml

__all__ = ["WhitelistManager", "WhitelistPattern"]


@dataclass
class WhitelistPattern:
    """A whitelisted command pattern.

    Attributes:
        pattern: The command pattern (exact string or regex)
        pattern_type: 'exact' for exact matches, 'regex' for regex patterns
        description: Human-readable description of what this pattern allows
        created_at: When this pattern was added (ISO format string)
        compiled: Compiled regex pattern (None for exact matches)
    """

    pattern: str
    pattern_type: Literal["exact", "regex"] = "exact"
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    compiled: re.Pattern[str] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Compile regex patterns after initialization."""
        if self.pattern_type == "regex":
            try:
                self.compiled = re.compile(self.pattern, re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{self.pattern}': {e}") from e

    def matches(self, command: str) -> bool:
        """Check if command matches this pattern.

        Args:
            command: Normalized command string to check

        Returns:
            True if command matches this pattern

        Example:
            >>> pattern = WhitelistPattern("git status", pattern_type="exact")
            >>> pattern.matches("git status")
            True
            >>> pattern.matches("git log")
            False
            >>> regex_pattern = WhitelistPattern("git.*", pattern_type="regex")
            >>> regex_pattern.matches("git status")
            True
            >>> regex_pattern.matches("git log")
            True
        """
        if self.pattern_type == "exact":
            return command == self.pattern
        else:
            # Regex pattern
            return self.compiled is not None and bool(self.compiled.search(command))


class WhitelistManager:
    """Manages whitelisted bash command patterns.

    Provides storage and matching for command whitelist with support for
    exact matches and regex patterns. Commands are normalized before matching
    to handle whitespace and quoting consistently.

    The whitelist is stored in YAML format at ~/.consoul/whitelist.yaml.

    Security Notes:
        - Whitelisted commands bypass approval prompts
        - Whitelisted commands still go through blocklist validation
        - Patterns should be as specific as possible
        - Regex patterns can be dangerous (e.g., ".*" whitelists everything)

    Example:
        >>> manager = WhitelistManager()
        >>> manager.add_pattern("git status", description="Safe read-only command")
        >>> manager.add_pattern("npm test", description="Run test suite")
        >>> manager.add_pattern("git (status|log|diff)", pattern_type="regex",
        ...                    description="Read-only git commands")
        >>> manager.is_whitelisted("git status")  # True
        >>> manager.is_whitelisted("rm -rf /")  # False
        >>> manager.save()  # Persist to ~/.consoul/whitelist.yaml
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize whitelist manager.

        Args:
            storage_path: Optional custom path for whitelist storage.
                         Defaults to ~/.consoul/whitelist.yaml
        """
        self.storage_path = (
            storage_path
            if storage_path
            else Path.home() / ".consoul" / "whitelist.yaml"
        )
        self.patterns: list[WhitelistPattern] = []
        self._pattern_cache: dict[str, bool] = {}  # Command -> is_whitelisted cache

        # Load existing whitelist if it exists
        if self.storage_path.exists():
            self.load()

    def add_pattern(
        self,
        pattern: str,
        pattern_type: Literal["exact", "regex"] = "exact",
        description: str = "",
    ) -> WhitelistPattern:
        """Add a command pattern to the whitelist.

        Args:
            pattern: Command pattern (exact string or regex)
            pattern_type: 'exact' for exact matches, 'regex' for regex patterns
            description: Human-readable description

        Returns:
            The created WhitelistPattern

        Raises:
            ValueError: If pattern is empty or regex pattern is invalid

        Example:
            >>> manager = WhitelistManager()
            >>> manager.add_pattern("git status")
            >>> manager.add_pattern("npm (install|ci)", pattern_type="regex")
        """
        if not pattern or not pattern.strip():
            raise ValueError("Pattern cannot be empty")

        # Normalize pattern for exact matches
        if pattern_type == "exact":
            pattern = self._normalize_command(pattern)

        # Check for duplicates
        for existing in self.patterns:
            if existing.pattern == pattern and existing.pattern_type == pattern_type:
                return existing  # Already exists

        # Create and add pattern
        whitelist_pattern = WhitelistPattern(
            pattern=pattern,
            pattern_type=pattern_type,
            description=description,
        )
        self.patterns.append(whitelist_pattern)

        # Clear cache since patterns changed
        self._pattern_cache.clear()

        return whitelist_pattern

    def remove_pattern(
        self, pattern: str, pattern_type: Literal["exact", "regex"] = "exact"
    ) -> bool:
        """Remove a pattern from the whitelist.

        Args:
            pattern: Pattern to remove
            pattern_type: Type of pattern to remove

        Returns:
            True if pattern was found and removed, False otherwise

        Example:
            >>> manager = WhitelistManager()
            >>> manager.add_pattern("git status")
            >>> manager.remove_pattern("git status")
            True
            >>> manager.remove_pattern("git status")
            False
        """
        # Normalize exact patterns
        if pattern_type == "exact":
            pattern = self._normalize_command(pattern)

        for i, existing in enumerate(self.patterns):
            if existing.pattern == pattern and existing.pattern_type == pattern_type:
                self.patterns.pop(i)
                self._pattern_cache.clear()
                return True

        return False

    def is_whitelisted(self, command: str) -> bool:
        """Check if command matches any whitelist pattern.

        Commands are normalized before matching (whitespace, quotes handled).
        Results are cached for performance.

        Args:
            command: Bash command to check

        Returns:
            True if command matches any whitelist pattern

        Example:
            >>> manager = WhitelistManager()
            >>> manager.add_pattern("git status")
            >>> manager.is_whitelisted("git status")
            True
            >>> manager.is_whitelisted("  git   status  ")  # Normalized
            True
            >>> manager.is_whitelisted("rm -rf /")
            False
        """
        # Normalize command
        normalized = self._normalize_command(command)

        # Check cache first
        if normalized in self._pattern_cache:
            return self._pattern_cache[normalized]

        # Check all patterns
        result = any(pattern.matches(normalized) for pattern in self.patterns)

        # Cache result
        self._pattern_cache[normalized] = result

        return result

    def get_patterns(self) -> list[WhitelistPattern]:
        """Get all whitelist patterns.

        Returns:
            List of WhitelistPattern objects

        Example:
            >>> manager = WhitelistManager()
            >>> manager.add_pattern("git status")
            >>> patterns = manager.get_patterns()
            >>> len(patterns)
            1
        """
        return self.patterns.copy()

    def clear(self) -> None:
        """Remove all patterns from whitelist.

        Example:
            >>> manager = WhitelistManager()
            >>> manager.add_pattern("git status")
            >>> manager.clear()
            >>> len(manager.get_patterns())
            0
        """
        self.patterns.clear()
        self._pattern_cache.clear()

    def save(self) -> None:
        """Save whitelist to storage file.

        Creates parent directory if it doesn't exist.
        Sets file permissions to 600 (user read/write only) for security.

        Raises:
            OSError: If file cannot be written

        Example:
            >>> manager = WhitelistManager()
            >>> manager.add_pattern("git status")
            >>> manager.save()  # Persists to ~/.consoul/whitelist.yaml
        """
        # Ensure parent directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert patterns to dict for YAML serialization
        data = {
            "version": 1,
            "patterns": [
                {
                    "pattern": p.pattern,
                    "pattern_type": p.pattern_type,
                    "description": p.description,
                    "created_at": p.created_at,
                }
                for p in self.patterns
            ],
        }

        # Write YAML
        with self.storage_path.open("w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        # Set secure permissions (user read/write only)
        self.storage_path.chmod(0o600)

    def load(self) -> None:
        """Load whitelist from storage file.

        Raises:
            ValueError: If file format is invalid or contains invalid patterns
            OSError: If file cannot be read

        Example:
            >>> manager = WhitelistManager()
            >>> manager.load()  # Loads from ~/.consoul/whitelist.yaml
        """
        if not self.storage_path.exists():
            return

        # Read YAML
        with self.storage_path.open("r") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError("Invalid whitelist file format: expected dict")

        # Validate version
        version = data.get("version", 1)
        if version != 1:
            raise ValueError(f"Unsupported whitelist file version: {version}")

        # Load patterns
        patterns_data = data.get("patterns", [])
        if not isinstance(patterns_data, list):
            raise ValueError("Invalid whitelist file format: patterns must be a list")

        self.patterns.clear()
        for pattern_dict in patterns_data:
            if not isinstance(pattern_dict, dict):
                continue

            try:
                pattern = WhitelistPattern(
                    pattern=pattern_dict.get("pattern", ""),
                    pattern_type=pattern_dict.get("pattern_type", "exact"),
                    description=pattern_dict.get("description", ""),
                    created_at=pattern_dict.get(
                        "created_at", datetime.now().isoformat()
                    ),
                )
                self.patterns.append(pattern)
            except (ValueError, TypeError) as e:
                # Skip invalid patterns but continue loading others
                import warnings

                warnings.warn(
                    f"Skipping invalid whitelist pattern: {e}",
                    UserWarning,
                    stacklevel=2,
                )

        # Clear cache after loading
        self._pattern_cache.clear()

    def _normalize_command(self, command: str) -> str:
        """Normalize command for consistent matching.

        Handles whitespace normalization and basic quote handling.

        Args:
            command: Raw command string

        Returns:
            Normalized command string

        Example:
            >>> manager = WhitelistManager()
            >>> manager._normalize_command("  ls  -la  ")
            'ls -la'
            >>> manager._normalize_command("echo 'hello world'")
            "echo 'hello world'"
        """
        # Strip leading/trailing whitespace
        command = command.strip()

        # Try to parse with shlex for proper quote handling
        try:
            tokens = shlex.split(command)
            # Rejoin with single spaces
            return " ".join(tokens)
        except ValueError:
            # If shlex parsing fails (unclosed quotes, etc.), fall back to simple normalization
            # Collapse multiple spaces to single space
            return " ".join(command.split())
