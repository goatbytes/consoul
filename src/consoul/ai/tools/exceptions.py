"""Exceptions for tool calling system.

Tool-specific exceptions for error handling in the tool registry,
execution, and validation workflows.
"""

from __future__ import annotations


class ToolError(Exception):
    """Base exception for all tool-related errors.

    This is the base class for all exceptions raised by the tool calling system.
    Catching this exception will catch all tool-related errors.
    """


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not registered.

    This error occurs when trying to access a tool that hasn't been
    registered in the ToolRegistry.

    Example:
        >>> registry.get_tool("nonexistent_tool")
        ToolNotFoundError: Tool 'nonexistent_tool' not found in registry
    """


class ToolExecutionError(ToolError):
    """Raised when tool execution fails.

    This error wraps exceptions that occur during tool execution,
    such as subprocess failures, timeouts, or runtime errors.

    Attributes:
        tool_name: Name of the tool that failed
        original_error: The underlying exception that caused the failure
    """

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initialize ToolExecutionError.

        Args:
            message: Human-readable error message
            tool_name: Name of the tool that failed (optional)
            original_error: The underlying exception (optional)
        """
        super().__init__(message)
        self.tool_name = tool_name
        self.original_error = original_error


class ToolValidationError(ToolError):
    """Raised when tool arguments fail validation.

    This error occurs when tool arguments don't match the expected schema
    or fail Pydantic validation.

    Example:
        >>> bash_tool.invoke({"command": 123})  # command must be string
        ToolValidationError: Invalid arguments for tool 'bash'
    """


class BlockedCommandError(ToolError):
    """Raised when a tool execution is blocked by security policy.

    This error occurs when a command is blocked by whitelist/blacklist
    rules, blocked command patterns (rm -rf, sudo, etc.), or other
    security policies.

    The command is blocked BEFORE user approval to prevent accidental
    execution of dangerous commands.

    Example:
        >>> bash_tool.invoke({"command": "sudo rm -rf /"})
        BlockedCommandError: Command blocked by security policy: 'sudo rm -rf /'
    """
