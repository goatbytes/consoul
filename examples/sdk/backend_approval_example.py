#!/usr/bin/env python3
"""Backend Approval Provider Example for Consoul SDK.

Demonstrates how to use custom approval providers with Consoul SDK for
web applications and backend services. Shows both CLI and Web approval
patterns side-by-side.

This example builds on web_approval_provider.py to show real-world integration
with Consoul SDK for backend applications (FastAPI, Flask, WebSocket, SSE).

Usage:
    # Terminal 1: Start approval server
    python examples/sdk/backend_approval_example.py --server

    # Terminal 2: Run SDK with web approval
    python examples/sdk/backend_approval_example.py --demo web

    # Or: Run SDK with default CLI approval
    python examples/sdk/backend_approval_example.py --demo cli

Requirements:
    pip install consoul aiohttp
"""

from __future__ import annotations

import argparse
import asyncio
import sys

# Add examples directory to path for imports
sys.path.insert(0, "examples/sdk")

from web_approval_provider import MockApprovalServer, WebApprovalProvider

from consoul import Consoul


def demo_cli_approval():
    """Demonstrate default CLI approval (traditional terminal workflow).

    This is the default behavior when no approval_provider is specified.
    User approval happens in terminal via input() prompts.
    """
    print("=" * 70)
    print("CLI Approval Demo (Default Behavior)")
    print("=" * 70)
    print()

    # Create Consoul with default CLI approval
    _console = Consoul(
        model="gpt-4o",
        tools=["bash"],  # Enable bash tool (requires approval)
        persist=False,
    )
    # approval_provider defaults to CliApprovalProvider(show_arguments=True)

    print("✓ Consoul SDK initialized with CLI approval")
    print("✓ Tools: bash (CAUTION level - requires approval)")
    print()
    print("When AI tries to execute bash commands, you'll see terminal prompts:")
    print("  - Tool name and arguments displayed")
    print("  - Prompt: 'Approve execution? (y/n):'")
    print("  - User responds via keyboard input")
    print()

    # Example: This would trigger CLI approval prompt
    # console.chat("List files in current directory")


async def demo_web_approval():
    """Demonstrate web approval provider (backend/API workflow).

    This shows how to integrate custom approval providers for web applications.
    Approval requests go to HTTP API instead of terminal prompts.
    """
    print("=" * 70)
    print("Web Approval Demo (Custom Provider)")
    print("=" * 70)
    print()

    # Create web approval provider pointing to running server
    web_provider = WebApprovalProvider(
        approval_url="http://localhost:8080/approve",
        auth_token="test-token",
        timeout=60,
    )

    # Create Consoul with custom web approval provider
    _console = Consoul(
        model="gpt-4o",
        tools=["bash", "grep"],  # Enable multiple tools
        approval_provider=web_provider,  # 🆕 Custom approval!
        persist=False,
    )

    print("✓ Consoul SDK initialized with WebApprovalProvider")
    print("✓ Approval endpoint: http://localhost:8080/approve")
    print("✓ Tools: bash, grep (both require approval)")
    print()
    print("When AI tries to execute tools, approval requests go to:")
    print("  - HTTP POST to approval_url")
    print("  - With Authorization header (Bearer token)")
    print("  - Server processes and returns approval decision")
    print()

    # Example: This would send approval request to web API
    # response = console.chat("List Python files")
    # print(f"Response: {response}")

    print("✓ Web approval workflow ready")
    print()
    print("In production, your web API would:")
    print("  1. Receive approval request from Consoul SDK")
    print("  2. Send notification to user (WebSocket, SSE, email)")
    print("  3. Show approval UI in web interface")
    print("  4. Return user's decision to SDK")
    print("  5. SDK executes or denies tool based on response")


def demo_custom_provider():
    """Demonstrate creating a simple custom approval provider.

    Shows the minimal interface needed to implement a custom provider.
    """
    print("=" * 70)
    print("Custom Provider Demo")
    print("=" * 70)
    print()

    from consoul.ai.tools.approval import (
        ToolApprovalRequest,
        ToolApprovalResponse,
    )

    class AlwaysApproveProvider:
        """DANGEROUS: Auto-approves all tools (testing only!)."""

        async def request_approval(
            self,
            request: ToolApprovalRequest,
        ) -> ToolApprovalResponse:
            print(f"  Auto-approving: {request.tool_name}")
            return ToolApprovalResponse(
                approved=True, reason="Auto-approved in test mode"
            )

    # Create Consoul with auto-approve provider
    auto_provider = AlwaysApproveProvider()
    _console = Consoul(
        model="gpt-4o", tools=["bash"], approval_provider=auto_provider, persist=False
    )

    print("✓ Consoul SDK initialized with AlwaysApproveProvider")
    print("⚠️  WARNING: All tools auto-approved (TESTING ONLY)")
    print()
    print("Custom providers need only one method:")
    print("  async def request_approval(self, request) -> ToolApprovalResponse")
    print()
    print("This enables:")
    print("  - Slack/Discord approval bots")
    print("  - Mobile app notifications")
    print("  - Automated approval rules")
    print("  - Custom audit logging")


def demo_fastapi_pattern():
    """Show FastAPI integration pattern (code example only)."""
    print("=" * 70)
    print("FastAPI Integration Pattern")
    print("=" * 70)
    print()
    print("Example FastAPI endpoint with Consoul SDK + Web Approval:")
    print()
    print('''
from fastapi import FastAPI, WebSocket
from consoul import Consoul
from examples.sdk.web_approval_provider import WebApprovalProvider

app = FastAPI()

# Initialize Consoul with web approval
web_provider = WebApprovalProvider(
    approval_url="https://api.example.com/tool-approval",
    auth_token="your-api-token"
)

console = Consoul(
    model="gpt-4o",
    tools=True,
    approval_provider=web_provider
)

@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for AI chat with tool execution."""
    await websocket.accept()

    while True:
        # Receive message from frontend
        user_message = await websocket.receive_text()

        # Send to AI (tools may need approval)
        response = console.chat(user_message)

        # Send response back to frontend
        await websocket.send_text(response)

# Tool approval endpoint (called by WebApprovalProvider)
@app.post("/tool-approval")
async def tool_approval(request: ToolApprovalRequest):
    """Handle tool approval requests from SDK."""
    # Store in database
    approval_id = save_approval_request(request)

    # Send notification to user via WebSocket
    await notify_user(request.user_id, approval_id)

    # Wait for user decision (polling or WebSocket)
    decision = await wait_for_decision(approval_id)

    return ToolApprovalResponse(
        approved=decision.approved,
        reason=decision.reason
    )
    ''')
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backend approval provider examples for Consoul SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start mock approval server
  %(prog)s --server

  # Demo CLI approval (default)
  %(prog)s --demo cli

  # Demo web approval (requires server running)
  %(prog)s --demo web

  # Demo custom provider
  %(prog)s --demo custom

  # Show FastAPI pattern
  %(prog)s --demo fastapi

Real-world usage:
  1. Implement approval provider for your backend (HTTP, WebSocket, etc.)
  2. Pass provider to Consoul(approval_provider=your_provider)
  3. Tool approval requests route through your approval system
  4. Users approve/deny via your web UI or API
        """,
    )

    parser.add_argument(
        "--server", action="store_true", help="Start mock approval server"
    )
    parser.add_argument(
        "--demo", choices=["cli", "web", "custom", "fastapi"], help="Run specific demo"
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve requests in server mode",
    )

    args = parser.parse_args()

    if args.server:
        # Start approval server
        print("\n🚀 Starting mock approval server...")
        print("   This simulates a backend approval API")
        print()
        server = MockApprovalServer(port=8080, auto_approve=args.auto_approve)
        asyncio.run(server.start())

    elif args.demo == "cli":
        demo_cli_approval()

    elif args.demo == "web":
        asyncio.run(demo_web_approval())

    elif args.demo == "custom":
        demo_custom_provider()

    elif args.demo == "fastapi":
        demo_fastapi_pattern()

    else:
        parser.print_help()
        print()
        print("Quick comparison:")
        print()
        print("CLI Approval (default):")
        print("  console = Consoul(tools=True)")
        print("  → Uses terminal prompts (CliApprovalProvider)")
        print()
        print("Web Approval (custom):")
        print(
            "  provider = WebApprovalProvider('https://api.example.com/approve', token)"
        )
        print("  console = Consoul(tools=True, approval_provider=provider)")
        print("  → Routes approvals to your web API")


if __name__ == "__main__":
    main()
