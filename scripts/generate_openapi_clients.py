#!/usr/bin/env python3
"""Export OpenAPI spec from Consoul server.

This script generates the OpenAPI specification from the server and writes it
to docs/api/openapi.json. Users can then use this spec to generate typed
clients in any language using tools like:

- Python: openapi-python-client generate --path docs/api/openapi.json
- TypeScript: openapi-generator-cli generate -i docs/api/openapi.json -g typescript-fetch
- Any language: https://openapi-generator.tech/docs/generators
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    """Export OpenAPI spec from server."""
    parser = argparse.ArgumentParser(
        description="Export OpenAPI spec from Consoul server"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("docs/api/openapi.json"),
        help="Output path for OpenAPI spec (default: docs/api/openapi.json)",
    )
    args = parser.parse_args()

    print("🔧 Generating OpenAPI spec from server...")
    try:
        from consoul.server import create_server

        app = create_server()
        spec = app.openapi()

        # Simplify operation IDs for cleaner method names
        simplify_operation_ids(spec)

        # Add missing request body for /chat endpoint
        # (Server uses Depends() which hides body from OpenAPI)
        add_chat_request_body(spec)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(spec, indent=2) + "\n")
        print(f"✅ OpenAPI spec written to {args.output}")

        print("\n📖 To generate a typed client:")
        print("   pip install openapi-python-client")
        print(f"   openapi-python-client generate --path {args.output}")

    except Exception as e:
        print(f"❌ Failed to generate OpenAPI spec: {e}", file=sys.stderr)
        return 1

    return 0


def add_chat_request_body(spec: dict[str, Any]) -> None:
    """Add ChatRequest body to /chat endpoint.

    The server uses Depends(get_chat_request) which manually parses the JSON body,
    hiding the schema from OpenAPI. This patches the spec to include the body.
    """
    chat_endpoint = spec.get("paths", {}).get("/chat", {}).get("post", {})
    if not chat_endpoint:
        return

    # Add ChatRequest schema to components if not present
    components = spec.setdefault("components", {})
    schemas = components.setdefault("schemas", {})

    if "ChatRequest" not in schemas:
        schemas["ChatRequest"] = {
            "type": "object",
            "title": "ChatRequest",
            "description": "Request body for POST /chat endpoint.",
            "required": ["session_id", "message"],
            "properties": {
                "session_id": {
                    "type": "string",
                    "title": "Session Id",
                    "description": "Unique session identifier. Auto-creates session if not exists.",
                    "minLength": 1,
                    "maxLength": 128,
                    "examples": ["user-abc123", "session-uuid-v4"],
                },
                "message": {
                    "type": "string",
                    "title": "Message",
                    "description": "User message to send to the AI (32KB max).",
                    "minLength": 1,
                    "maxLength": 32768,
                    "examples": ["Hello, how are you?"],
                },
                "model": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Model",
                    "description": "Model to use (only applies when creating new session).",
                    "default": None,
                    "examples": ["gpt-4o", "claude-3-5-sonnet-20241022"],
                },
            },
        }

    # Add requestBody to the endpoint
    chat_endpoint["requestBody"] = {
        "required": True,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/ChatRequest"}}
        },
    }

    # Fix operationId to be cleaner (FastAPI uses dependency name)
    chat_endpoint["operationId"] = "chat"


def simplify_operation_ids(spec: dict[str, Any]) -> None:
    """Simplify FastAPI operation IDs for cleaner method names.

    FastAPI generates IDs like "health_check_health_get" -> "health_check"
    """
    for path_data in spec.get("paths", {}).values():
        for operation in path_data.values():
            if isinstance(operation, dict) and "operationId" in operation:
                op_id = operation["operationId"]
                # Remove trailing HTTP method and path suffix
                # e.g., "chat_chat_post" -> "chat"
                parts = op_id.rsplit("_", 2)
                if len(parts) >= 2 and parts[-1] in (
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                ):
                    operation["operationId"] = "_".join(parts[:-1]).rstrip("_")


if __name__ == "__main__":
    sys.exit(main())
