# SDK Integration Examples

This directory contains examples for integrating Consoul SDK with common frameworks and patterns.

## Quick Start

| Use Case | Example |
|----------|---------|
| FastAPI backend with sessions | [`fastapi_backend.py`](fastapi_backend.py) |
| Flask backend with sessions | [`flask_backend.py`](flask_backend.py) |
| Pure async without web framework | [`async_usage.py`](async_usage.py) |
| Custom tools in backends | [`custom_tools.py`](custom_tools.py) |

## API Level Comparison

| Feature | `Consoul` | `ConversationService` |
|---------|-----------|------------------------|
| Simplicity | High | Medium |
| Streaming | No | Yes (`async for`) |
| Session persistence | Built-in | Manual |
| Control | High-level | Low-level |
| Best for | HTTP endpoints | WebSocket/streaming |

**When to use `Consoul`:**
- Simple request-response pattern (HTTP endpoints)
- Built-in session management with `create_session()`/`restore_session()`
- Quick integration without async complexity

**When to use `ConversationService`:**
- Token-by-token streaming required
- WebSocket or SSE endpoints
- Fine-grained control over conversation state
- Concurrent conversation handling

## Example Descriptions

### `fastapi_backend.py`
Full FastAPI integration with:
- HTTP chat endpoint (`POST /chat`)
- WebSocket streaming with tool approval
- Session persistence (in-memory for demo)
- Health endpoints

```bash
pip install consoul[server] fastapi uvicorn
python examples/sdk/integrations/fastapi_backend.py
curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{"session_id": "user1", "message": "Hello"}'
```

### `flask_backend.py`
Flask integration with:
- HTTP chat endpoint (`POST /chat`)
- Session management
- Cost tracking
- Error handling

```bash
pip install consoul flask flask-cors
python examples/sdk/integrations/flask_backend.py
curl -X POST http://localhost:5000/chat \
    -H "Content-Type: application/json" \
    -d '{"session_id": "user1", "message": "Hello"}'
```

### `async_usage.py`
Pure async patterns with:
- `ConversationService.from_config()`
- `async for` token streaming
- `asyncio.gather` for concurrent conversations
- Tool approval callbacks
- `ToolFilter` sandboxing

```bash
pip install consoul
python examples/sdk/integrations/async_usage.py
```

### `custom_tools.py`
Custom tool registration with:
- `@tool` decorator for simple functions
- `BaseTool` class for advanced control
- `ToolFilter` for per-session sandboxing
- Risk level and category mapping
- Backend approval patterns

```bash
pip install consoul
python examples/sdk/integrations/custom_tools.py
```

## Security Checklist

All examples use development-friendly settings. For production:

- [ ] Replace wildcard CORS with specific origins
- [ ] Add API authentication (JWT, API keys)
- [ ] Use Redis for distributed session storage
- [ ] Enable HTTPS/TLS
- [ ] Implement rate limiting
- [ ] Add request logging and monitoring
- [ ] Use secure session_id generation (UUID v4)
- [ ] Provide `approval_provider` when `tools=True`

## Key Imports

```python
# High-level API (simple)
from consoul.sdk import Consoul, create_session, restore_session, save_session_state

# Service layer (advanced)
from consoul.sdk import ConversationService, Token, ToolRequest

# Tool filtering
from consoul.sdk import ToolFilter
from consoul.ai.tools.base import RiskLevel, ToolCategory

# Custom tools
from langchain_core.tools import tool, BaseTool
```

## See Also

- [`examples/backend/fastapi_sessions.py`](../../backend/fastapi_sessions.py) - Full-featured FastAPI example
- [`examples/sdk/tool_specification/`](../tool_specification/) - Detailed tool examples
- [`examples/sdk/session_hooks/`](../session_hooks/) - Session lifecycle hooks
