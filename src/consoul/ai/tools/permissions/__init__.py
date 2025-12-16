"""Permission management system for tool calling.

This module provides SDK components for managing tool execution permissions,
including dynamic risk assessment, whitelisting, and policy-based approvals.

The permission system is SDK-first and has no TUI dependencies, making it
reusable across different applications.

Example:
    >>> from consoul.ai.tools.permissions import CommandAnalyzer, WhitelistManager
    >>> analyzer = CommandAnalyzer()
    >>> risk = analyzer.analyze_command("ls -la")
    >>> assert risk.level == RiskLevel.SAFE
    >>>
    >>> manager = WhitelistManager()
    >>> manager.add_pattern("git status")
    >>> manager.is_whitelisted("git status")
    True
"""

from consoul.ai.tools.permissions.analyzer import CommandAnalyzer, CommandRisk
from consoul.ai.tools.permissions.policy import (
    PermissionPolicy,
    PolicyResolver,
    PolicySettings,
)
from consoul.ai.tools.permissions.whitelist import WhitelistManager, WhitelistPattern

__all__ = [
    "CommandAnalyzer",
    "CommandRisk",
    "PermissionPolicy",
    "PolicyResolver",
    "PolicySettings",
    "WhitelistManager",
    "WhitelistPattern",
]
