#!/usr/bin/env python3
"""Simple WebSocket client for testing Consoul FastAPI server.

Connects to the FastAPI WebSocket server and provides an interactive
chat interface with tool approval support.

Usage:
    python examples/fastapi_websocket_client.py

    # Or specify server URL
    python examples/fastapi_websocket_client.py --url ws://localhost:8000/ws/chat

Requirements:
    pip install websockets
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys

try:
    import websockets
except ImportError:
    print("Error: websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


class ConsoulWebSocketClient:
    """Interactive WebSocket client for Consoul chat server."""

    def __init__(self, url: str):
        """Initialize client.

        Args:
            url: WebSocket server URL (e.g., ws://localhost:8000/ws/chat)
        """
        self.url = url
        self.websocket = None

    async def connect(self):
        """Connect to WebSocket server."""
        print(f"Connecting to {self.url}...")
        self.websocket = await websockets.connect(self.url)
        print("Connected! ✓")
        print()

    async def send_message(self, content: str):
        """Send user message to server.

        Args:
            content: User message text
        """
        await self.websocket.send(json.dumps({"type": "message", "content": content}))

    async def send_approval(self, tool_call_id: str, approved: bool):
        """Send tool approval response to server.

        Args:
            tool_call_id: ID of the tool call to approve/deny
            approved: True to approve, False to deny
        """
        await self.websocket.send(
            json.dumps(
                {"type": "tool_approval", "id": tool_call_id, "approved": approved}
            )
        )

    async def receive_messages(self):
        """Receive and handle messages from server."""
        async for message in self.websocket:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "token":
                # AI response token - print without newline
                content = data.get("content", "")
                print(content, end="", flush=True)

            elif message_type == "tool_request":
                # Tool execution approval request
                print()  # New line before approval prompt
                print()
                print("=" * 70)
                print("TOOL EXECUTION REQUEST")
                print("=" * 70)
                print(f"Tool: {data.get('name')}")
                print(f"Risk Level: {data.get('risk_level')}")
                print(f"Arguments: {json.dumps(data.get('arguments', {}), indent=2)}")
                print("=" * 70)

                # Prompt user for approval
                while True:
                    response = input("Approve execution? [y/n]: ").strip().lower()
                    if response in ("y", "n"):
                        approved = response == "y"
                        await self.send_approval(data.get("id"), approved)
                        if approved:
                            print("✓ Approved - executing tool...")
                        else:
                            print("✗ Denied - skipping tool execution")
                        print()
                        break
                    print("Please enter 'y' or 'n'")

            elif message_type == "done":
                # Response complete
                print()  # New line after final token
                print()

            elif message_type == "error":
                # Error message
                print()
                print(f"Error: {data.get('message')}", file=sys.stderr)
                print()

            else:
                print(f"Unknown message type: {message_type}", file=sys.stderr)

    async def run_interactive(self):
        """Run interactive chat session."""
        print("=" * 70)
        print("Consoul WebSocket Chat Client")
        print("=" * 70)
        print()
        print("Commands:")
        print("  Type your message and press Enter to send")
        print("  Type 'quit' or 'exit' to disconnect")
        print("  Press Ctrl+C to force quit")
        print()
        print("=" * 70)
        print()

        try:
            await self.connect()

            # Start message receiver task
            receiver_task = asyncio.create_task(self.receive_messages())

            # Interactive input loop
            while True:
                try:
                    # Get user input (blocking)
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, input, "You: "
                    )

                    # Check for quit commands
                    if user_input.strip().lower() in ("quit", "exit"):
                        print("Disconnecting...")
                        break

                    if user_input.strip():
                        # Send message to server
                        await self.send_message(user_input)
                        print()  # Blank line before AI response
                        print("AI: ", end="", flush=True)

                except EOFError:
                    # Ctrl+D pressed
                    print()
                    print("Disconnecting...")
                    break

            # Cancel receiver task
            receiver_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receiver_task

        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket error: {e}", file=sys.stderr)
        except KeyboardInterrupt:
            print()
            print("Interrupted - disconnecting...")
        finally:
            if self.websocket:
                await self.websocket.close()
            print("Disconnected")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="WebSocket client for Consoul chat server"
    )
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/ws/chat",
        help="WebSocket server URL (default: ws://localhost:8000/ws/chat)",
    )
    args = parser.parse_args()

    client = ConsoulWebSocketClient(args.url)
    await client.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Exiting...")
