#!/usr/bin/env python3
"""Basic Consoul Server - Minimal factory pattern usage.

Demonstrates the simplest way to create a production-ready Consoul server.

Usage:
    python examples/sdk/backend/basic_server.py

    # Test health endpoint
    curl http://localhost:8000/health

    # Test readiness endpoint
    curl http://localhost:8000/ready

Environment Variables:
    CONSOUL_API_KEYS: Comma-separated API keys (optional)
    REDIS_URL: Redis URL for sessions/rate limiting (optional)
"""

from consoul.server import create_server

# Create server with environment-based configuration
# All settings are loaded from environment variables
app = create_server()


# The factory provides these built-in endpoints:
# - GET /health - Liveness probe
# - GET /ready - Readiness probe (checks Redis if configured)
# - POST /chat - Chat endpoint with session management
# - WS /ws/chat/{session_id} - WebSocket streaming


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Consoul Basic Server")
    print("=" * 60)
    print()
    print("Built-in endpoints:")
    print("  GET  http://localhost:8000/health")
    print("  GET  http://localhost:8000/ready")
    print("  POST http://localhost:8000/chat")
    print("  WS   ws://localhost:8000/ws/chat/{session_id}")
    print()
    print("Test with:")
    print("  curl http://localhost:8000/health")
    print()
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
