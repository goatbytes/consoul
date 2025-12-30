#!/usr/bin/env python3
"""Custom Tools Integration Example.

Demonstrates registering custom tools with Consoul SDK for backend use.

Features:
    - @tool decorator for simple functions
    - BaseTool class for advanced control
    - Mixing custom tools with built-in tools
    - Tool approval patterns for backends
    - ToolFilter for per-session sandboxing
    - Risk level and category mapping

Usage:
    pip install consoul
    python examples/sdk/integrations/custom_tools.py

Security Notes:
    - Custom tools should validate all inputs
    - Use ToolFilter to restrict available tools per session
    - Set appropriate risk levels for custom tools
    - Approval providers are REQUIRED when tools=True in backends
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from consoul import Consoul
from consoul.ai.tools.base import RiskLevel, ToolCategory
from consoul.sdk import ToolFilter

# =============================================================================
# Example 1: Simple @tool decorator
# =============================================================================


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city.

    Args:
        city: Name of the city to get weather for

    Returns:
        Weather information as a string
    """
    # In a real app, this would call a weather API
    return f"Weather in {city}: 72°F, sunny with light clouds"


@tool
def calculate_tip(amount: str, percentage: str = "18") -> str:
    """Calculate tip for a bill.

    Args:
        amount: Bill amount in dollars (e.g., "50.00")
        percentage: Tip percentage (default: "18")

    Returns:
        Tip amount and total
    """
    try:
        bill = float(amount)
        pct = float(percentage)
        tip = bill * (pct / 100)
        return f"Bill: ${bill:.2f}, Tip ({pct}%): ${tip:.2f}, Total: ${bill + tip:.2f}"
    except ValueError:
        return "Invalid input. Use numbers only."


# =============================================================================
# Example 2: BaseTool class for advanced control
# =============================================================================


class DatabaseQueryTool(BaseTool):
    """Execute read-only database queries.

    Advanced tool example with input validation and error handling.
    """

    name: str = "query_database"
    description: str = (
        "Execute a read-only SQL SELECT query. Only SELECT statements are allowed."
    )

    def _run(self, query: str) -> str:
        """Execute the query with validation."""
        # Validate query is read-only
        normalized = query.strip().upper()
        if not normalized.startswith("SELECT"):
            return "Error: Only SELECT queries are allowed for security."

        # Check for dangerous patterns
        dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE"]
        for keyword in dangerous:
            if keyword in normalized:
                return f"Error: {keyword} is not allowed in read-only mode."

        # In a real app, execute against actual database
        return (
            f"Query executed: {query}\nResults: (mock data - implement DB connection)"
        )


class TextAnalysisTool(BaseTool):
    """Analyze text for sentiment and statistics."""

    name: str = "analyze_text"
    description: str = "Analyze text for word count, character count, and basic stats."

    def _run(self, text: str) -> str:
        """Analyze the input text."""
        words = text.split()
        sentences = text.count(".") + text.count("!") + text.count("?")
        return (
            f"Words: {len(words)}, "
            f"Characters: {len(text)}, "
            f"Sentences: {sentences or 1}, "
            f"Avg words/sentence: {len(words) / (sentences or 1):.1f}"
        )


# =============================================================================
# Example 3: Register tools with Consoul
# =============================================================================


def example_basic_registration():
    """Basic tool registration with Consoul."""
    print("=== Basic Tool Registration ===\n")

    # Mix custom tools with built-in tools
    console = Consoul(
        model="gpt-4o-mini",
        tools=[
            get_weather,  # Custom @tool
            calculate_tip,  # Custom @tool
            DatabaseQueryTool(),  # Custom BaseTool
            "web_search",  # Built-in tool by name
        ],
        # Map custom tools to risk levels
        tool_risk_mapping={
            "get_weather": RiskLevel.SAFE,
            "calculate_tip": RiskLevel.SAFE,
            "query_database": RiskLevel.CAUTION,  # Requires oversight
        },
        # Map custom tools to categories
        tool_categories_mapping={
            "get_weather": [ToolCategory.WEB],
            "calculate_tip": [ToolCategory.SEARCH],  # General utility
            "query_database": [ToolCategory.SEARCH],
        },
    )

    print(f"Registered tools: {console.settings.get('tools', [])}")
    print()


# =============================================================================
# Example 4: ToolFilter for per-session sandboxing
# =============================================================================


def example_tool_filter():
    """Using ToolFilter to restrict tools per session."""
    print("=== ToolFilter for Sandboxing ===\n")

    # Create a restrictive filter for a specific use case
    # (e.g., customer support that shouldn't execute code)
    support_filter = ToolFilter(
        # Blocklist - these tools are never allowed
        deny=["bash_execute", "file_edit", "file_write", "query_database"],
        # Allowlist - only these tools are allowed (if specified)
        allow=["get_weather", "calculate_tip", "web_search"],
        # Maximum risk level allowed
        risk_level=RiskLevel.SAFE,
        # Only allow certain categories
        categories=[ToolCategory.WEB, ToolCategory.SEARCH],
    )

    console = Consoul(
        model="gpt-4o-mini",
        tools=[get_weather, calculate_tip, "web_search", "bash_execute"],
        tool_filter=support_filter,
    )

    print(f"Model: {console.settings.get('model')}")
    print("Filter applied: Only safe, read-only tools allowed")
    print(f"Denied: {support_filter.deny}")
    print(f"Allowed: {support_filter.allow}")
    print()


# =============================================================================
# Example 5: Backend approval pattern
# =============================================================================


def example_backend_approval():
    """Approval pattern for web backends.

    In backends, you MUST provide an approval_provider when tools are enabled,
    otherwise tool calls will block waiting for CLI input.
    """
    print("=== Backend Approval Pattern ===\n")

    class AutoApproveProvider:
        """Auto-approve safe tools, deny dangerous ones."""

        async def on_tool_request(self, request) -> bool:
            """Approve based on risk level."""
            # Auto-approve safe tools
            if request.risk_level == "safe":
                print(f"Auto-approved: {request.name}")
                return True
            # Deny dangerous tools
            if request.risk_level == "dangerous":
                print(f"Auto-denied: {request.name}")
                return False
            # For caution-level, you might queue for human review
            print(f"Needs review: {request.name}")
            return False

    console = Consoul(
        model="gpt-4o-mini",
        tools=[get_weather, "web_search"],
        approval_provider=AutoApproveProvider(),
        tool_risk_mapping={
            "get_weather": RiskLevel.SAFE,
        },
    )

    print(f"Model: {console.settings.get('model')}")
    print("Approval provider configured for automated tool approval")
    print()


def main():
    """Run all examples."""
    example_basic_registration()
    example_tool_filter()
    example_backend_approval()

    print("=== Summary ===")
    print(
        """
Key patterns for custom tools in backends:

1. Use @tool decorator for simple functions
2. Use BaseTool class for input validation and error handling
3. Always set risk levels for custom tools
4. Use ToolFilter for per-session restrictions
5. ALWAYS provide approval_provider when tools=True in backends
6. Mix custom tools with built-in tools by name
"""
    )


if __name__ == "__main__":
    main()
