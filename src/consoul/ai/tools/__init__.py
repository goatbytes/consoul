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
from consoul.ai.tools.audit import (
    AuditEvent,
    AuditLogger,
    FileAuditLogger,
    NullAuditLogger,
)
from consoul.ai.tools.base import RiskLevel, ToolMetadata
from consoul.ai.tools.cache import CACHE_VERSION, CacheStats, CodeSearchCache
from consoul.ai.tools.catalog import (
    get_all_tool_names,
    get_tool_by_name,
    get_tools_by_risk_level,
    validate_tool_name,
)
from consoul.ai.tools.exceptions import (
    BlockedCommandError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)
from consoul.ai.tools.implementations.bash import bash_execute
from consoul.ai.tools.implementations.code_search import code_search
from consoul.ai.tools.implementations.file_edit import (
    append_to_file,
    create_file,
    delete_file,
    edit_file_lines,
    edit_file_search_replace,
)
from consoul.ai.tools.implementations.find_references import find_references
from consoul.ai.tools.implementations.grep_search import grep_search
from consoul.ai.tools.implementations.read_url import read_url
from consoul.ai.tools.implementations.web_search import web_search
from consoul.ai.tools.parser import (
    ParsedToolCall,
    has_tool_calls,
    parse_tool_calls,
)
from consoul.ai.tools.permissions.analyzer import CommandAnalyzer, CommandRisk
from consoul.ai.tools.permissions.policy import (
    PermissionPolicy,
    PolicyResolver,
    PolicySettings,
)
from consoul.ai.tools.permissions.whitelist import WhitelistManager, WhitelistPattern
from consoul.ai.tools.registry import ToolRegistry
from consoul.ai.tools.status import ToolStatus

__all__ = [
    "CACHE_VERSION",
    "ApprovalError",
    "ApprovalProvider",
    "AuditEvent",
    "AuditLogger",
    "BlockedCommandError",
    "CacheStats",
    "CodeSearchCache",
    "CommandAnalyzer",
    "CommandRisk",
    "FileAuditLogger",
    "NullAuditLogger",
    "ParsedToolCall",
    "PermissionPolicy",
    "PolicyResolver",
    "PolicySettings",
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
    "append_to_file",
    "bash_execute",
    "code_search",
    "create_file",
    "delete_file",
    "edit_file_lines",
    "edit_file_search_replace",
    "find_references",
    "get_all_tool_names",
    "get_tool_by_name",
    "get_tools_by_risk_level",
    "grep_search",
    "has_tool_calls",
    "parse_tool_calls",
    "read_url",
    "validate_tool_name",
    "web_search",
]
