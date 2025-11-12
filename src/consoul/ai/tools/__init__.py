"""Tool calling system for Consoul AI.

This module provides a centralized tool registry and configuration system
for LangChain tool calling. It enables AI models to execute tools (bash commands,
Python code, file operations) with security controls, user approval, and audit logging.

Architecture:
- SDK-first design: No TUI dependencies, works in headless environments
- Protocol-based extension points: ApprovalProvider, AuditLogger
- Security-first: Always require approval, blocked commands, timeouts
- Configuration: Tools configured via ConsoulConfig (not TUI-specific)

Example:
    >>> from consoul.config.models import ConsoulConfig, ToolConfig
    >>> from consoul.ai.tools import ToolRegistry, RiskLevel
    >>> from consoul.ai.tools.providers import CliApprovalProvider
    >>>
    >>> config = ConsoulConfig(
    ...     profiles={"default": ...},
    ...     tools=ToolConfig(enabled=True, timeout=30)
    ... )
    >>> provider = CliApprovalProvider()
    >>> registry = ToolRegistry(config.tools, approval_provider=provider)
    >>> # Register tools, bind to model, execute with approval
"""

from consoul.ai.tools.approval import (
    ApprovalError,
    ApprovalProvider,
    ToolApprovalRequest,
    ToolApprovalResponse,
)
from consoul.ai.tools.base import RiskLevel, ToolMetadata
from consoul.ai.tools.exceptions import (
    BlockedCommandError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)
from consoul.ai.tools.implementations.bash import bash_execute
from consoul.ai.tools.parser import (
    ParsedToolCall,
    has_tool_calls,
    parse_tool_calls,
)
from consoul.ai.tools.permissions.analyzer import CommandAnalyzer, CommandRisk
from consoul.ai.tools.permissions.whitelist import WhitelistManager, WhitelistPattern
from consoul.ai.tools.registry import ToolRegistry
from consoul.ai.tools.status import ToolStatus

__all__ = [
    "ApprovalError",
    "ApprovalProvider",
    "BlockedCommandError",
    "CommandAnalyzer",
    "CommandRisk",
    "ParsedToolCall",
    "RiskLevel",
    "ToolApprovalRequest",
    "ToolApprovalResponse",
    "ToolError",
    "ToolExecutionError",
    "ToolMetadata",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolStatus",
    "ToolValidationError",
    "WhitelistManager",
    "WhitelistPattern",
    "bash_execute",
    "has_tool_calls",
    "parse_tool_calls",
]
