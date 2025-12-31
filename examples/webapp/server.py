#!/usr/bin/env python3
"""Minimal Consoul web app server.

Run with: python server.py
Then open: http://localhost:8000
"""

from pathlib import Path

import uvicorn
from fastapi.responses import FileResponse

from consoul.server import create_server

# Create Consoul server with all middleware pre-configured
app = create_server()

# Serve the frontend
STATIC_DIR = Path(__file__).parent


@app.get("/")
async def index() -> FileResponse:
    """Serve the chat UI."""
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    print("Starting Consoul Web App...")
    print("Open http://localhost:8000 in your browser")
    print("\nEnvironment variables:")
    print("  ANTHROPIC_API_KEY or OPENAI_API_KEY - Required for AI")
    print("  CONSOUL_API_KEYS - Optional API key auth")
    uvicorn.run(app, host="0.0.0.0", port=8000)
