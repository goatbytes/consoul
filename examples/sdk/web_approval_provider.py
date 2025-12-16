#!/usr/bin/env python3
"""Web-Based Approval Provider Example.

Demonstrates implementing HTTP-based approval workflow for web applications.
The AI requests approval via HTTP API, and a web UI handles user decisions.

Usage:
    # Start mock approval server
    python examples/sdk/web_approval_provider.py --server

    # Use web approval in your application
    from examples.sdk.web_approval_provider import WebApprovalProvider
    provider = WebApprovalProvider("http://localhost:8080/approve", "token")

Requirements:
    pip install consoul aiohttp
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import aiohttp
from aiohttp import web

from consoul.ai.tools.approval import (
    ToolApprovalRequest,
    ToolApprovalResponse,
)


class WebApprovalProvider:
    """HTTP-based approval provider for web applications.

    Sends approval requests to a web API endpoint and waits for user decision.
    Suitable for web applications, microservices, and distributed systems.

    Example:
        >>> provider = WebApprovalProvider(
        ...     approval_url="https://api.example.com/tool-approval",
        ...     auth_token="your-api-token"
        ... )
        >>> registry = ToolRegistry(config, approval_provider=provider)
    """

    def __init__(
        self,
        approval_url: str,
        auth_token: str,
        timeout: int = 60,
    ):
        """Initialize web approval provider.

        Args:
            approval_url: HTTP endpoint to send approval requests
            auth_token: Authentication token for API requests
            timeout: Request timeout in seconds
        """
        self.approval_url = approval_url
        self.auth_token = auth_token
        self.timeout = timeout

    async def request_approval(
        self, request: ToolApprovalRequest
    ) -> ToolApprovalResponse:
        """Send approval request to web API.

        Args:
            request: Tool approval request

        Returns:
            ToolApprovalResponse from web API
        """
        payload = {
            "tool_call_id": request.tool_call_id,
            "tool_name": request.tool_name,
            "arguments": request.arguments,
            "risk_level": request.risk_level.value,
            "description": request.description,
            "context": request.context,
        }

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    self.approval_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.auth_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    return ToolApprovalResponse(
                        approved=data["approved"],
                        reason=data.get("reason"),
                        timeout_override=data.get("timeout_override"),
                        metadata=data.get("metadata", {}),
                    )
                else:
                    error_text = await resp.text()
                    return ToolApprovalResponse(
                        approved=False,
                        reason=f"HTTP {resp.status}: {error_text}",
                    )

        except asyncio.TimeoutError:
            return ToolApprovalResponse(
                approved=False,
                reason=f"Approval request timed out after {self.timeout}s",
            )
        except aiohttp.ClientError as e:
            return ToolApprovalResponse(
                approved=False,
                reason=f"Network error: {e}",
            )
        except Exception as e:
            return ToolApprovalResponse(
                approved=False,
                reason=f"Unexpected error: {e}",
            )


# =============================================================================
# Mock Approval Server (for testing)
# =============================================================================


class MockApprovalServer:
    """Mock HTTP server for testing web approval workflow.

    Simulates a web application's approval API endpoint.
    In production, replace with your actual web framework (Flask, FastAPI, etc.)
    """

    def __init__(self, port: int = 8080, auto_approve: bool = False):
        """Initialize mock server.

        Args:
            port: Port to listen on
            auto_approve: If True, auto-approve all requests (for testing)
        """
        self.port = port
        self.auto_approve = auto_approve
        self.pending_requests: dict[str, dict[str, Any]] = {}

    async def handle_approval_request(self, request: web.Request) -> web.Response:
        """Handle incoming approval requests."""
        # Verify auth token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.json_response(
                {"error": "Missing or invalid authorization"},
                status=401,
            )

        token = auth_header.replace("Bearer ", "")
        if token != "test-token":  # In production, verify against real tokens
            return web.json_response(
                {"error": "Invalid token"},
                status=403,
            )

        # Parse request
        data = await request.json()
        tool_call_id = data.get("tool_call_id")

        print("\n" + "=" * 70)
        print("Approval Request Received")
        print("=" * 70)
        print(f"Tool: {data.get('tool_name')}")
        print(f"Risk Level: {data.get('risk_level')}")
        print(f"Arguments: {json.dumps(data.get('arguments'), indent=2)}")
        print("=" * 70)

        # Auto-approve mode (for testing)
        if self.auto_approve:
            print("✓ Auto-approved (test mode)")
            return web.json_response(
                {
                    "approved": True,
                    "reason": "Auto-approved in test mode",
                }
            )

        # Store for manual approval (in production, store in database)
        self.pending_requests[tool_call_id] = data

        # In production, this would:
        # 1. Store request in database
        # 2. Send notification to user (email, websocket, etc.)
        # 3. Wait for user decision via UI
        # 4. Return approval response

        # For this demo, we'll simulate immediate approval
        approved = True  # In production, wait for real user decision

        response_data = {
            "approved": approved,
            "reason": "Approved via web UI" if approved else "Denied by user",
            "metadata": {
                "approved_at": "2025-11-12T10:00:00Z",
                "approved_by": "user@example.com",
            },
        }

        print(f"→ Response: {'Approved' if approved else 'Denied'}")
        print()

        return web.json_response(response_data)

    async def start(self) -> None:
        """Start the mock approval server."""
        app = web.Application()
        app.router.add_post("/approve", self.handle_approval_request)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, "localhost", self.port)
        await site.start()

        print(f"🚀 Mock approval server running at http://localhost:{self.port}")
        print(f"   Endpoint: http://localhost:{self.port}/approve")
        print("   Auth token: test-token")
        print(f"   Auto-approve: {self.auto_approve}")
        print("\nPress Ctrl+C to stop...")
        print()

        # Keep server running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            await runner.cleanup()


# =============================================================================
# Demo Usage
# =============================================================================


async def demo_web_approval() -> None:
    """Demonstrate web approval provider usage."""
    from consoul.ai.tools import RiskLevel, ToolRegistry, bash_execute
    from consoul.ai.tools.permissions import PermissionPolicy
    from consoul.config.models import ToolConfig

    print("Web Approval Provider Demo")
    print("=" * 70)
    print()

    # Create web approval provider
    provider = WebApprovalProvider(
        approval_url="http://localhost:8080/approve",
        auth_token="test-token",
        timeout=60,
    )

    # Create tool registry
    config = ToolConfig(
        enabled=True,
        permission_policy=PermissionPolicy.BALANCED,
        audit_logging=False,
    )

    registry = ToolRegistry(config=config, approval_provider=provider)
    registry.register(bash_execute, risk_level=RiskLevel.CAUTION)

    print("✓ Registry created with WebApprovalProvider")
    print("✓ Approval endpoint: http://localhost:8080/approve")
    print()

    # Test approval
    print("Testing approval workflow...")
    print()

    response = await registry.request_tool_approval(
        tool_name="bash_execute",
        arguments={"command": "ls -la"},
    )

    print(f"Approval result: {'Approved' if response.approved else 'Denied'}")
    if response.reason:
        print(f"Reason: {response.reason}")
    print()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Web-based approval provider example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start mock server (auto-approve for testing)
  %(prog)s --server --auto-approve

  # Start mock server (manual approval simulation)
  %(prog)s --server

  # Run approval demo (requires server running)
  %(prog)s --demo
        """,
    )

    parser.add_argument(
        "--server",
        action="store_true",
        help="Start mock approval server",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run approval demo",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve all requests (test mode)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Server port (default: 8080)",
    )

    args = parser.parse_args()

    if args.server:
        # Start server
        server = MockApprovalServer(
            port=args.port,
            auto_approve=args.auto_approve,
        )
        asyncio.run(server.start())
    elif args.demo:
        # Run demo
        asyncio.run(demo_web_approval())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
