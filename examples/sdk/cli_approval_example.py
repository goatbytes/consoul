#!/usr/bin/env python3
"""CLI Tool with Custom Approval - Complete Example.

This example demonstrates building a CLI tool using Consoul SDK with
terminal-based approval prompts. Perfect for command-line applications
that need AI capabilities with user control.

Usage:
    python examples/sdk/cli_approval_example.py "What files are in this directory?"
    python examples/sdk/cli_approval_example.py --verbose "Show git status"

Requirements:
    pip install consoul langchain-anthropic
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from consoul.ai.tools import RiskLevel, ToolRegistry, bash_execute
from consoul.ai.tools.permissions import PermissionPolicy
from consoul.ai.tools.providers import CliApprovalProvider
from consoul.config.loader import load_config
from consoul.config.models import ToolConfig


def create_tool_registry(verbose: bool = False) -> ToolRegistry:
    """Create tool registry with CLI approval provider.

    Args:
        verbose: Show detailed tool information in approval prompts

    Returns:
        Configured ToolRegistry instance
    """
    # Load configuration
    try:
        config = load_config()
        tool_config = config.tools
    except Exception as e:
        print(f"Warning: Could not load config: {e}")
        print("Using default configuration...")
        # Fallback to default config
        tool_config = ToolConfig(
            enabled=True,
            permission_policy=PermissionPolicy.BALANCED,
            audit_logging=True,
        )

    # Create CLI approval provider
    approval_provider = CliApprovalProvider(
        show_arguments=True,
        verbose=verbose,
    )

    # Create registry with custom approval provider
    registry = ToolRegistry(
        config=tool_config,
        approval_provider=approval_provider,
    )

    # Register bash tool
    registry.register(
        tool=bash_execute,
        risk_level=RiskLevel.CAUTION,
        tags=["system", "bash"],
    )

    print(f"✓ Tool registry created with {len(registry.list_tools())} tools")
    print("✓ Approval provider: CliApprovalProvider")
    print(f"✓ Permission policy: {tool_config.permission_policy.value}")
    print(f"✓ Audit logging: {tool_config.audit_logging}")
    print()

    return registry


async def chat_with_tools(query: str, verbose: bool = False) -> None:
    """Run a query with tool calling enabled.

    Args:
        query: User's question/request
        verbose: Show detailed information
    """
    # Create registry
    registry = create_tool_registry(verbose=verbose)

    # Import model (lazy to avoid requiring API key for --help)
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        print("Error: langchain-anthropic not installed")
        print("Install with: pip install langchain-anthropic")
        sys.exit(1)

    # Check for API key
    import os

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Set with: export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    # Create model with tools
    model = ChatAnthropic(model="claude-3-5-sonnet-20241022")
    model_with_tools = registry.bind_tools(model)

    print("=" * 70)
    print(f"Query: {query}")
    print("=" * 70)
    print()

    try:
        # Invoke model
        response = await asyncio.to_thread(model_with_tools.invoke, query)

        print("\n" + "=" * 70)
        print("Response:")
        print("=" * 70)
        print(response.content)
        print()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="CLI tool with AI and tool calling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "List files in the current directory"
  %(prog)s --verbose "Show git status"
  %(prog)s "Create a new directory called test"

Environment Variables:
  ANTHROPIC_API_KEY    Your Anthropic API key (required)
        """,
    )

    parser.add_argument("query", help="Your question or request")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed approval information",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="CLI Approval Example 1.0",
    )

    args = parser.parse_args()

    # Run async chat
    try:
        asyncio.run(chat_with_tools(args.query, verbose=args.verbose))
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
