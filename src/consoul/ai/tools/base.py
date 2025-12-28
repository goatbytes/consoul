"""Base classes and utilities for tool calling system.

Provides core data structures, enums, and utility functions used across
the tool calling implementation.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


class RiskLevel(str, Enum):
    """Risk assessment level for tool execution.

    Used to classify tools based on their potential impact and inform
    user approval workflows with appropriate warnings.

    Attributes:
        SAFE: Low-risk operations (ls, pwd, echo, cat read-only files)
        CAUTION: Medium-risk operations (mkdir, cp, mv, git commit)
        DANGEROUS: High-risk operations (rm -rf, dd, kill -9, chmod 777)
        BLOCKED: Explicitly prohibited operations (sudo, rm -rf /, fork bombs)
    """

    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"

    def __str__(self) -> str:
        """Return string representation of risk level."""
        return self.value


class ToolCategory(str, Enum):
    """Functional categories for tool classification.

    Used to group tools by their primary purpose, enabling category-based
    tool filtering in the SDK.

    Attributes:
        SEARCH: Search and lookup tools (grep, code_search, find_references)
        FILE_EDIT: File manipulation tools (create, edit, delete, append)
        WEB: Web-based tools (read_url, web_search)
        EXECUTE: Command execution tools (bash_execute)
    """

    SEARCH = "search"
    FILE_EDIT = "file-edit"
    WEB = "web"
    EXECUTE = "execute"

    def __str__(self) -> str:
        """Return string representation of category."""
        return self.value


@dataclass
class ToolMetadata:
    """Metadata for a registered tool.

    Stores information about a tool's configuration, schema, risk level,
    and the underlying LangChain tool instance.

    Attributes:
        name: Tool name (used for lookups and binding to models)
        description: Human-readable description of what the tool does
        risk_level: Security risk classification
        tool: The LangChain BaseTool instance
        schema: JSON schema for tool arguments (auto-generated from tool)
        enabled: Whether this tool is currently enabled
        tags: Optional tags for categorization (e.g., ["filesystem", "readonly"])
        categories: Optional functional categories for grouping tools
    """

    name: str
    description: str
    risk_level: RiskLevel
    tool: BaseTool
    schema: dict[str, Any]
    enabled: bool = True
    tags: list[str] | None = None
    categories: list[ToolCategory] | None = None

    def __post_init__(self) -> None:
        """Validate metadata after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Tool name cannot be empty")
        if not self.description:
            raise ValueError("Tool description cannot be empty")


def get_tool_schema(tool: BaseTool) -> dict[str, Any]:
    """Extract JSON schema from LangChain tool.

    Args:
        tool: LangChain BaseTool instance

    Returns:
        JSON schema dictionary for tool arguments

    Example:
        >>> from langchain_core.tools import tool
        >>> @tool
        ... def my_tool(x: int, y: str) -> str:
        ...     '''Example tool'''
        ...     return f"{y}: {x}"
        >>> schema = get_tool_schema(my_tool)
        >>> assert "properties" in schema
    """
    # LangChain tools have args_schema which is a Pydantic model
    if hasattr(tool, "args_schema") and tool.args_schema:
        # args_schema could be BaseModel type or dict
        args_schema = tool.args_schema
        if isinstance(args_schema, dict):
            return args_schema
        schema: dict[str, Any] = args_schema.model_json_schema()
        return schema

    # Fallback: try to get schema from tool directly
    if hasattr(tool, "get_input_schema"):
        schema = tool.get_input_schema().model_json_schema()
        return schema

    # If no schema available, return empty schema
    return {"type": "object", "properties": {}}


# -----------------------------------------------------------------------------
# Cooperative Cancellation Infrastructure
# -----------------------------------------------------------------------------
#
# Python threads cannot be forcibly stopped. This infrastructure enables
# *cooperative* cancellation - tools must periodically call check_cancelled()
# to respond to cancellation requests.
#
# Usage in custom tools:
#     from consoul.ai.tools import check_cancelled
#
#     @tool
#     def my_long_running_tool(data: str) -> str:
#         for chunk in process_chunks(data):
#             check_cancelled()  # Exit early if cancelled
#             results.append(analyze(chunk))
#         return summarize(results)
# -----------------------------------------------------------------------------

# Thread-local storage for cancellation flags
# Maps thread ident -> threading.Event
_cancellation_flags: dict[int, threading.Event] = {}
_flags_lock = threading.Lock()  # Thread-safe access


def get_cancellation_flag() -> threading.Event | None:
    """Get cancellation flag for current thread.

    Returns the Event associated with the current thread's tool execution,
    or None if no cancellation flag is registered (e.g., not running in
    the tool execution context).

    Returns:
        The Event for current thread, or None if not set.

    Example:
        >>> flag = get_cancellation_flag()
        >>> if flag and flag.is_set():
        ...     # Clean up and exit
        ...     return "Cancelled"
    """
    thread_id = threading.current_thread().ident
    if thread_id is None:
        return None
    return _cancellation_flags.get(thread_id)


def check_cancelled() -> None:
    """Check if cancellation was requested for current tool execution.

    Call this periodically in long-running tools to enable graceful cancellation.
    This is the recommended way to support cooperative cancellation.

    Raises:
        asyncio.CancelledError: If cancellation was requested.

    Example:
        >>> from consoul.ai.tools import check_cancelled
        >>> from langchain_core.tools import tool
        >>>
        >>> @tool
        ... def my_long_running_tool(input: str) -> str:
        ...     '''Process data with cancellation support.'''
        ...     for i in range(1000):
        ...         check_cancelled()  # Raises if cancelled
        ...         do_work(i)
        ...     return "done"
    """
    flag = get_cancellation_flag()
    if flag is not None and flag.is_set():
        raise asyncio.CancelledError("Tool execution cancelled")


def _register_cancellation_flag(flag: threading.Event) -> None:
    """Register cancellation flag for current thread. Internal use only.

    Called by ConversationService before executing a tool in the thread pool.
    The flag is set when timeout or cancellation occurs, allowing cooperative
    tools to check and exit gracefully.

    Args:
        flag: The Event to register for this thread.
    """
    thread_id = threading.current_thread().ident
    if thread_id is None:
        return  # Cannot register without thread ID
    with _flags_lock:
        _cancellation_flags[thread_id] = flag


def _unregister_cancellation_flag() -> None:
    """Unregister cancellation flag for current thread. Internal use only.

    Called by ConversationService after tool execution completes (in finally block).
    Prevents memory leaks from accumulating flags for completed executions.
    """
    thread_id = threading.current_thread().ident
    if thread_id is None:
        return  # Cannot unregister without thread ID
    with _flags_lock:
        _cancellation_flags.pop(thread_id, None)
