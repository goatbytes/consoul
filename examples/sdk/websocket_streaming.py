#!/usr/bin/env python3
"""WebSocket Streaming Example using async_stream_events().

Demonstrates low-level WebSocket integration with Consoul SDK using the
async_stream_events() API (SOUL-234) and custom approval providers (SOUL-235).

This example shows the lower-level streaming API compared to the high-level
ConversationService used in examples/fastapi_websocket_server.py.

Key Features:
- Direct usage of async_stream_events() for fine-grained control
- WebSocket-based tool approval workflow
- Token-by-token streaming to web clients
- Concurrent message receiver (prevents approval deadlock)
- Embedded HTML test client

Usage:
    # Install dependencies
    pip install consoul fastapi uvicorn websockets

    # Start server
    python examples/sdk/websocket_streaming.py

    # Open browser
    http://localhost:8000/

    # Or save HTML client
    python examples/sdk/websocket_streaming.py --save-client

Architecture Comparison:
    ConversationService (high-level):
        - Manages conversation history automatically
        - Handles message formatting
        - Integrated cost tracking
        - See: examples/fastapi_websocket_server.py

    async_stream_events (low-level):
        - Direct control over message list
        - Event-based streaming protocol
        - Manual conversation management
        - See: This file

Requirements:
    pip install consoul fastapi uvicorn websockets
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

if TYPE_CHECKING:
    from consoul.ai.tools.approval import ToolApprovalRequest, ToolApprovalResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Consoul WebSocket Streaming Example",
    description="Low-level WebSocket streaming using async_stream_events()",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebSocketApprovalProvider:
    """WebSocket-based approval provider for tool execution.

    Implements the tool approval protocol to send approval requests via
    WebSocket and wait for client responses.

    This is a simplified version compared to examples/fastapi_websocket_server.py,
    focused on demonstrating the approval provider pattern with async_stream_events().

    Example:
        >>> provider = WebSocketApprovalProvider(websocket)
        >>> # Tool approval requests will be sent via websocket
        >>> # and responses awaited before tool execution
    """

    def __init__(self, websocket: WebSocket, timeout: float = 60.0):
        """Initialize WebSocket approval provider.

        Args:
            websocket: Active WebSocket connection
            timeout: Maximum seconds to wait for approval response
        """
        self.websocket = websocket
        self.timeout = timeout
        self._pending_approvals: dict[str, asyncio.Future[bool]] = {}

    async def request_approval(
        self, request: ToolApprovalRequest
    ) -> ToolApprovalResponse:
        """Request approval for tool execution via WebSocket.

        Args:
            request: Tool approval request with name, args, and risk level

        Returns:
            ToolApprovalResponse with approval decision
        """
        from consoul.ai.tools.approval import ToolApprovalResponse

        # Create future to wait for client response
        approval_future: asyncio.Future[bool] = asyncio.Future()
        self._pending_approvals[request.tool_name] = approval_future

        # Send approval request to client
        try:
            await self.websocket.send_json(
                {
                    "type": "tool_request",
                    "tool": request.tool_name,
                    "arguments": request.arguments,
                    "risk_level": request.risk_level,
                }
            )

            # Wait for client response with timeout
            approved = await asyncio.wait_for(approval_future, timeout=self.timeout)

            return ToolApprovalResponse(
                approved=approved,
                reason="Approved by user" if approved else "Denied by user",
            )

        except asyncio.TimeoutError:
            logger.warning(
                f"Tool approval timeout for {request.tool_name} (60s timeout)"
            )
            return ToolApprovalResponse(approved=False, reason="Approval timeout")
        except Exception as e:
            logger.error(f"Error requesting tool approval: {e}")
            return ToolApprovalResponse(approved=False, reason=f"Error: {e}")
        finally:
            # Clean up pending approval
            self._pending_approvals.pop(request.tool_name, None)

    def handle_approval_response(self, tool_name: str, approved: bool) -> None:
        """Handle approval response from client.

        Args:
            tool_name: Name of tool being approved/denied
            approved: True if approved, False if denied
        """
        future = self._pending_approvals.get(tool_name)
        if future and not future.done():
            future.set_result(approved)


# HTML test client (embedded)
HTML_CLIENT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Consoul WebSocket Streaming Test</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        #chat {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            min-height: 400px;
            max-height: 600px;
            overflow-y: auto;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .message {
            margin: 15px 0;
            padding: 10px;
            border-radius: 4px;
        }
        .user {
            background: #e3f2fd;
            text-align: right;
        }
        .assistant {
            background: #f5f5f5;
        }
        .tool-request {
            background: #fff3cd;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 15px 0;
        }
        .tool-buttons {
            margin-top: 10px;
        }
        .tool-buttons button {
            margin-right: 10px;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        .approve {
            background: #4CAF50;
            color: white;
        }
        .deny {
            background: #f44336;
            color: white;
        }
        #input-container {
            display: flex;
            gap: 10px;
        }
        #input {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        #send {
            padding: 12px 24px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        #send:hover {
            background: #45a049;
        }
        #send:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            text-align: center;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .connected {
            background: #d4edda;
            color: #155724;
        }
        .disconnected {
            background: #f8d7da;
            color: #721c24;
        }
        code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <h1>🚀 Consoul WebSocket Streaming</h1>
    <div id="status" class="status disconnected">Connecting...</div>
    <div id="chat"></div>
    <div id="input-container">
        <input id="input" type="text" placeholder="Type your message..." disabled>
        <button id="send" disabled>Send</button>
    </div>

    <script>
        let ws = null;
        let currentMessage = '';

        function connect() {
            ws = new WebSocket('ws://localhost:8000/ws');

            ws.onopen = () => {
                console.log('Connected to WebSocket');
                setStatus('Connected', true);
                document.getElementById('input').disabled = false;
                document.getElementById('send').disabled = false;
            };

            ws.onclose = () => {
                console.log('Disconnected from WebSocket');
                setStatus('Disconnected - Refresh to reconnect', false);
                document.getElementById('input').disabled = true;
                document.getElementById('send').disabled = true;
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                setStatus('Connection Error', false);
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                handleMessage(msg);
            };
        }

        function setStatus(text, connected) {
            const status = document.getElementById('status');
            status.textContent = text;
            status.className = 'status ' + (connected ? 'connected' : 'disconnected');
        }

        function handleMessage(msg) {
            if (msg.type === 'token') {
                // Accumulate token
                currentMessage += msg.data.text;
                updateAssistantMessage(currentMessage);
            } else if (msg.type === 'tool_call') {
                // Tool call completed
                addSystemMessage(`🔧 Tool Call: ${msg.data.name}`);
            } else if (msg.type === 'tool_request') {
                // Tool approval request
                showToolApproval(msg);
            } else if (msg.type === 'done') {
                // Message complete
                finalizeAssistantMessage();
                currentMessage = '';
            } else if (msg.type === 'error') {
                addSystemMessage('❌ Error: ' + msg.message);
            }
        }

        function addUserMessage(text) {
            const chat = document.getElementById('chat');
            const div = document.createElement('div');
            div.className = 'message user';
            div.textContent = text;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function updateAssistantMessage(text) {
            const chat = document.getElementById('chat');
            let lastMessage = chat.lastElementChild;

            if (!lastMessage || !lastMessage.classList.contains('assistant-current')) {
                lastMessage = document.createElement('div');
                lastMessage.className = 'message assistant assistant-current';
                chat.appendChild(lastMessage);
            }

            lastMessage.textContent = text;
            chat.scrollTop = chat.scrollHeight;
        }

        function finalizeAssistantMessage() {
            const chat = document.getElementById('chat');
            const lastMessage = chat.lastElementChild;
            if (lastMessage && lastMessage.classList.contains('assistant-current')) {
                lastMessage.classList.remove('assistant-current');
            }
        }

        function addSystemMessage(text) {
            const chat = document.getElementById('chat');
            const div = document.createElement('div');
            div.className = 'message';
            div.textContent = text;
            div.style.fontStyle = 'italic';
            div.style.color = '#666';
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function showToolApproval(msg) {
            const chat = document.getElementById('chat');
            const div = document.createElement('div');
            div.className = 'tool-request';

            const title = document.createElement('strong');
            title.textContent = '🔐 Tool Approval Request';
            div.appendChild(title);

            const details = document.createElement('div');
            details.innerHTML = `
                <p><strong>Tool:</strong> <code>${msg.tool}</code></p>
                <p><strong>Risk Level:</strong> ${msg.risk_level}</p>
                <p><strong>Arguments:</strong> <code>${JSON.stringify(msg.arguments)}</code></p>
            `;
            div.appendChild(details);

            const buttons = document.createElement('div');
            buttons.className = 'tool-buttons';

            const approveBtn = document.createElement('button');
            approveBtn.className = 'approve';
            approveBtn.textContent = '✓ Approve';
            approveBtn.onclick = () => sendApproval(msg.tool, true, div);

            const denyBtn = document.createElement('button');
            denyBtn.className = 'deny';
            denyBtn.textContent = '✗ Deny';
            denyBtn.onclick = () => sendApproval(msg.tool, false, div);

            buttons.appendChild(approveBtn);
            buttons.appendChild(denyBtn);
            div.appendChild(buttons);

            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function sendApproval(tool, approved, div) {
            ws.send(JSON.stringify({
                type: 'tool_approval',
                tool: tool,
                approved: approved
            }));

            div.style.opacity = '0.5';
            const buttons = div.querySelector('.tool-buttons');
            buttons.innerHTML = approved ? '✓ Approved' : '✗ Denied';
        }

        function sendMessage() {
            const input = document.getElementById('input');
            const text = input.value.trim();

            if (!text) return;

            addUserMessage(text);

            ws.send(JSON.stringify({
                type: 'message',
                content: text
            }));

            input.value = '';
        }

        // Event listeners
        document.getElementById('send').addEventListener('click', sendMessage);
        document.getElementById('input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Connect on load
        connect();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_client():
    """Serve HTML test client."""
    return HTML_CLIENT


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "consoul-websocket-streaming"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for AI chat using async_stream_events().

    Protocol:
        Client → Server:
            {"type": "message", "content": "user message"}
            {"type": "tool_approval", "tool": "tool_name", "approved": true}

        Server → Client:
            {"type": "token", "data": {"text": "chunk"}}
            {"type": "tool_call", "data": {"name": "tool", "args": {...}}}
            {"type": "tool_request", "tool": "tool_name", "arguments": {...}, "risk_level": "..."}
            {"type": "done", "data": {...}}
            {"type": "error", "message": "error details"}
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established: {websocket.client}")

    # Import SDK components (demonstrates low-level usage)
    from consoul.ai import get_chat_model
    from consoul.ai.async_streaming import async_stream_events
    from consoul.ai.tools import ToolRegistry

    # Initialize model
    try:
        model = get_chat_model("gpt-4o-mini")
    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        await websocket.send_json(
            {"type": "error", "message": f"Failed to initialize model: {e}"}
        )
        return

    # Create tool registry with bash tool
    from consoul.config import ConsoulConfig

    config = ConsoulConfig()
    config.tools.allowed_tools = ["bash"]  # Enable bash for testing
    tool_registry = ToolRegistry(config)

    # Bind tools to model
    tools = tool_registry.get_tools()
    if tools:
        model = model.bind_tools(tools)

    # Create approval provider
    approval_provider = WebSocketApprovalProvider(websocket)

    # Conversation messages (manual management)
    messages: list = []

    # Queue for incoming user messages
    message_queue: asyncio.Queue[dict] = asyncio.Queue()

    async def receive_messages():
        """Background task: continuously receive and route incoming messages."""
        try:
            while True:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "message":
                    # Queue user messages for processing
                    await message_queue.put(data)
                elif message_type == "tool_approval":
                    # Handle tool approval immediately (non-blocking)
                    tool_name = data.get("tool")
                    approved = data.get("approved", False)
                    logger.info(
                        f"Tool approval response: tool={tool_name}, approved={approved}"
                    )
                    approval_provider.handle_approval_response(tool_name, approved)
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        }
                    )
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected in receiver task")
        except Exception as e:
            logger.error(f"Error in receiver task: {e}", exc_info=True)

    async def process_messages():
        """Main task: process queued user messages and stream responses."""
        try:
            while True:
                # Get next user message from queue
                data = await message_queue.get()
                user_content = data.get("content", "")
                logger.info(f"Processing message: {user_content[:100]}")

                # Add user message to conversation
                messages.append({"role": "user", "content": user_content})

                try:
                    # Stream events using low-level API
                    async for event in async_stream_events(model, messages):
                        # Send event to client
                        await websocket.send_json(
                            {"type": event.type, "data": event.data}
                        )

                        # For "done" event, add AI message to conversation
                        if event.type == "done":
                            ai_message = event.data.get("message")
                            if ai_message:
                                messages.append(
                                    {"role": "assistant", "content": ai_message.content}
                                )

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    await websocket.send_json({"type": "error", "message": str(e)})

        except Exception as e:
            logger.error(f"Error in processor task: {e}", exc_info=True)

    # Run receiver and processor concurrently (prevents approval deadlock)
    receiver_task = asyncio.create_task(receive_messages())
    processor_task = asyncio.create_task(process_messages())

    try:
        # Wait for either task to complete (disconnect or error)
        _done, pending = await asyncio.wait(
            [receiver_task, processor_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        with contextlib.suppress(Exception):
            await websocket.send_json(
                {"type": "error", "message": f"Server error: {e}"}
            )
    finally:
        logger.info("WebSocket connection closed")


def save_html_client(path: str = "websocket_test.html"):
    """Save HTML test client to file.

    Args:
        path: Output file path
    """
    with open(path, "w") as f:
        f.write(HTML_CLIENT)
    print(f"✓ HTML client saved to: {path}")
    print(f"  Open in browser: file://{path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="WebSocket streaming example using async_stream_events()",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server (HTML client at http://localhost:8000/)
  %(prog)s

  # Save HTML client to file
  %(prog)s --save-client websocket_test.html

Architecture Comparison:
  High-level (ConversationService):
    - Automatic conversation history management
    - Integrated cost tracking
    - See: examples/fastapi_websocket_server.py

  Low-level (async_stream_events):
    - Direct control over message list
    - Event-based streaming protocol
    - Manual conversation management
    - See: This file
        """,
    )

    parser.add_argument(
        "--save-client", nargs="?", const="websocket_test.html", help="Save HTML client"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")

    args = parser.parse_args()

    if args.save_client:
        save_html_client(args.save_client)
        return

    # Start server
    import uvicorn

    print("=" * 70)
    print("Consoul WebSocket Streaming Example")
    print("=" * 70)
    print()
    print("Using async_stream_events() for low-level streaming control")
    print()
    print(f"Server: http://{args.host}:{args.port}/")
    print(f"WebSocket: ws://{args.host}:{args.port}/ws")
    print(f"Health: http://{args.host}:{args.port}/health")
    print()
    print("Open in browser: http://localhost:8000/")
    print()
    print("Compare to:")
    print("  - examples/fastapi_websocket_server.py (ConversationService)")
    print("  - This file (async_stream_events)")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
