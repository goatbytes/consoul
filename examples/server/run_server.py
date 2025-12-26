#!/usr/bin/env python3
"""Simple server startup script for testing.

Starts the Consoul server with a test API key for local development.

Usage:
    python examples/server/run_server.py

    # Or with custom port
    python examples/server/run_server.py --port 8080

Then open examples/server/test_client.html in your browser.

Test API Key: test-key-123
"""

import argparse
import logging

import uvicorn

from consoul.server import create_server
from consoul.server.models import SecurityConfig, ServerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Test API key for development
TEST_API_KEY = "test-key-123"


def main() -> None:
    """Start the test server."""
    parser = argparse.ArgumentParser(description="Run Consoul test server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--no-auth", action="store_true", help="Disable API key auth")
    args = parser.parse_args()

    # Create config with test API key
    if args.no_auth:
        config = ServerConfig()
        print("\n" + "=" * 60)
        print("SERVER RUNNING (NO AUTHENTICATION)")
        print("=" * 60)
    else:
        config = ServerConfig(
            security=SecurityConfig(api_keys=[TEST_API_KEY]),
        )
        print("\n" + "=" * 60)
        print("SERVER RUNNING WITH TEST AUTHENTICATION")
        print(f"API Key: {TEST_API_KEY}")
        print("=" * 60)

    print("\nEndpoints:")
    print(f"  Health:    http://{args.host}:{args.port}/health")
    print(f"  HTTP Chat: http://{args.host}:{args.port}/chat")
    print(f"  WebSocket: ws://{args.host}:{args.port}/ws/chat/{{session_id}}")
    print("\nOpen test_client.html in your browser to test.")
    print("=" * 60 + "\n")

    # Create and run server
    app = create_server(config)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
