"""Base classes and utilities for tool calling system.

Provides core data structures, enums, and utility functions used across
the tool calling implementation.
"""

from __future__ import annotations

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
        CAUTION: Medium-risk operations (grep, find, network requests)
        DANGEROUS: High-risk operations (rm, sudo, chmod, write operations)
    """

    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"

    def __str__(self) -> str:
        """Return string representation of risk level."""
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
    """

    name: str
    description: str
    risk_level: RiskLevel
    tool: BaseTool
    schema: dict[str, Any]
    enabled: bool = True
    tags: list[str] | None = None

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
        schema: dict[str, Any] = tool.args_schema.model_json_schema()
        return schema

    # Fallback: try to get schema from tool directly
    if hasattr(tool, "get_input_schema"):
        schema = tool.get_input_schema().model_json_schema()
        return schema

    # If no schema available, return empty schema
    return {"type": "object", "properties": {}}
