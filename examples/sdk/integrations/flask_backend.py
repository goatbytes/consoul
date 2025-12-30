#!/usr/bin/env python3
"""Flask Backend Integration Example.

Demonstrates Consoul SDK integration with Flask for multi-user backends.

Features:
    - HTTP chat endpoint with session management
    - Session persistence with create_session/restore_session
    - Cost tracking via console.last_cost
    - Error handling with proper HTTP status codes
    - Session cleanup endpoint

Usage:
    pip install consoul flask flask-cors
    python examples/sdk/integrations/flask_backend.py

    # Test chat endpoint:
    curl -X POST http://localhost:5000/chat \
        -H "Content-Type: application/json" \
        -d '{"session_id": "user1", "message": "Hello"}'

    # Get session info:
    curl http://localhost:5000/sessions/user1

    # Delete session:
    curl -X DELETE http://localhost:5000/sessions/user1

Security Notes:
    ⚠️  DEVELOPMENT CONFIGURATION - Not production-ready

    - Wildcard CORS (allows any origin)
    - No authentication
    - In-memory sessions (not distributed)
    - Debug mode enabled

    REQUIRED for Production:
    - Specific CORS origins
    - API authentication (JWT, API keys)
    - Redis session storage
    - HTTPS/TLS
    - Disable debug mode
"""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS

from consoul.sdk import create_session, restore_session, save_session_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ⚠️ DEVELOPMENT ONLY - Replace with specific origins in production
CORS(app, resources={r"/*": {"origins": "*"}})

# In-memory session store (use Redis in production)
sessions: dict[str, dict[str, Any]] = {}


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat message with session persistence.

    Request JSON:
        {
            "session_id": "user123",
            "message": "Hello!"
        }

    Response JSON:
        {
            "session_id": "user123",
            "response": "Hi! How can I help you?",
            "tokens": {"input": 10, "output": 15},
            "cost": 0.00025
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    session_id = data.get("session_id")
    message = data.get("message")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    if not message:
        return jsonify({"error": "message required"}), 400

    # Restore or create session
    if session_id in sessions:
        logger.info(f"Restoring session: {session_id}")
        console = restore_session(sessions[session_id])
    else:
        logger.info(f"Creating new session: {session_id}")
        console = create_session(
            session_id=session_id,
            model="gpt-4o-mini",  # Cost-effective for demos
            tools=False,  # Chat-only mode (safe for backends)
        )

    # Send message and get response
    response = console.chat(message)

    # Persist session state
    sessions[session_id] = save_session_state(console)

    # Get cost info
    cost_info = console.last_cost

    return jsonify(
        {
            "session_id": session_id,
            "response": str(response),
            "tokens": {
                "input": cost_info.get("input_tokens", 0),
                "output": cost_info.get("output_tokens", 0),
            },
            "cost": cost_info.get("total_cost", 0.0),
        }
    )


@app.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """Get session information."""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    state = sessions[session_id]
    return jsonify(
        {
            "session_id": session_id,
            "message_count": len(state.get("history", [])),
            "model": state.get("model", "unknown"),
        }
    )


@app.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """Delete a session."""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    del sessions[session_id]
    logger.info(f"Deleted session: {session_id}")
    return jsonify({"status": "deleted", "session_id": session_id})


@app.route("/sessions", methods=["GET"])
def list_sessions():
    """List all active sessions."""
    return jsonify(
        {
            "count": len(sessions),
            "sessions": list(sessions.keys()),
        }
    )


if __name__ == "__main__":
    # ⚠️ DEVELOPMENT ONLY - Use gunicorn/uwsgi in production
    app.run(host="0.0.0.0", port=5000, debug=True)
