#!/usr/bin/env python3
"""Pure Async Usage Example.

Demonstrates ConversationService for low-level async streaming without web frameworks.

Features:
    - Direct ConversationService usage
    - async for token streaming
    - Concurrent conversation handling with asyncio.gather
    - Tool approval callback pattern
    - Cost tracking via get_stats()

Usage:
    pip install consoul
    python examples/sdk/integrations/async_usage.py

    # Or run specific examples:
    python -c "import asyncio; from async_usage import stream_response; asyncio.run(stream_response())"

Security Notes:
    - Tool approval callback controls what tools can execute
    - Use ToolFilter for fine-grained tool sandboxing
    - Risk levels: "safe" < "caution" < "dangerous"
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from consoul.sdk import ConversationService, ToolFilter

if TYPE_CHECKING:
    from consoul.sdk.models import ToolRequest


async def stream_response():
    """Basic streaming example with ConversationService.

    Shows how to stream AI responses token by token.
    """
    print("=== Basic Streaming ===\n")

    service = ConversationService.from_config(
        custom_system_prompt="You are a helpful assistant. Keep responses brief.",
        include_tool_docs=False,  # No tools for this example
        include_env_context=False,
        include_git_context=False,
    )

    try:
        async for token in service.send_message("What is the capital of France?"):
            print(token.content, end="", flush=True)
        print("\n")

        # Get stats
        stats = service.get_stats()
        print(f"Messages: {stats.message_count}")
        print(f"Tokens: {stats.total_tokens}")
    finally:
        # Cleanup resources
        if hasattr(service, "executor") and service._owns_executor:
            service.executor.shutdown(wait=False)


async def with_tool_approval():
    """Streaming with tool approval callback.

    Shows how to approve/deny tool execution requests.
    """
    print("\n=== Tool Approval ===\n")

    async def approve_tool(request: ToolRequest) -> bool:
        """Approve only safe tools."""
        print(f"Tool request: {request.name} (risk: {request.risk_level})")
        # Only approve safe tools
        return request.risk_level == "safe"

    service = ConversationService.from_config(
        custom_system_prompt="You are a helpful assistant with tool access.",
        include_tool_docs=True,
        include_env_context=False,
        include_git_context=False,
    )

    try:
        async for token in service.send_message(
            "Search the web for 'Python asyncio tutorial'",
            on_tool_request=approve_tool,
        ):
            print(token.content, end="", flush=True)
        print("\n")
    finally:
        if hasattr(service, "executor") and service._owns_executor:
            service.executor.shutdown(wait=False)


async def concurrent_conversations():
    """Handle multiple conversations concurrently.

    Shows how to use asyncio.gather for parallel conversations.
    """
    print("\n=== Concurrent Conversations ===\n")

    async def run_conversation(name: str, question: str):
        """Run a single conversation."""
        service = ConversationService.from_config(
            custom_system_prompt="You are a helpful assistant. Give brief answers.",
            include_tool_docs=False,
            include_env_context=False,
            include_git_context=False,
        )

        response_parts = []
        try:
            async for token in service.send_message(question):
                response_parts.append(token.content)
        finally:
            if hasattr(service, "executor") and service._owns_executor:
                service.executor.shutdown(wait=False)

        response = "".join(response_parts)
        return f"{name}: {response}"

    # Run multiple conversations in parallel
    results = await asyncio.gather(
        run_conversation("User1", "What is 2+2?"),
        run_conversation("User2", "What is the color of the sky?"),
        run_conversation("User3", "Name a fruit"),
    )

    for result in results:
        print(result)
        print("-" * 40)


async def with_tool_filter():
    """Using ToolFilter for per-session sandboxing.

    Shows how to restrict which tools are available.
    """
    print("\n=== Tool Filter ===\n")

    # Create a filter that only allows safe, read-only tools
    safe_filter = ToolFilter(
        deny=["bash_execute", "file_edit", "file_write"],  # Blocklist
        allow=["web_search", "grep_search"],  # Allowlist
    )

    service = ConversationService.from_config(
        custom_system_prompt="You have limited tool access.",
        tool_filter=safe_filter,
        include_env_context=False,
        include_git_context=False,
    )

    try:
        async for token in service.send_message("What tools do you have access to?"):
            print(token.content, end="", flush=True)
        print("\n")
    finally:
        if hasattr(service, "executor") and service._owns_executor:
            service.executor.shutdown(wait=False)


async def main():
    """Run all examples."""
    await stream_response()
    await concurrent_conversations()
    # Uncomment to test tool features (requires API key):
    # await with_tool_approval()
    # await with_tool_filter()


if __name__ == "__main__":
    asyncio.run(main())
