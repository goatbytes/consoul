"""Permission management system for tool calling.

This module provides SDK components for managing tool execution permissions,
including dynamic risk assessment, whitelisting, and policy-based approvals.

The permission system is SDK-first and has no TUI dependencies, making it
reusable across different applications.

Example:
    >>> from consoul.ai.tools.permissions import CommandAnalyzer
    >>> analyzer = CommandAnalyzer()
    >>> risk = analyzer.analyze_command("ls -la")
    >>> assert risk.level == RiskLevel.SAFE
"""

from consoul.ai.tools.permissions.analyzer import CommandAnalyzer, CommandRisk

__all__ = ["CommandAnalyzer", "CommandRisk"]
