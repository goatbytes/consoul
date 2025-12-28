# Backend Deployment Guide

This guide covers deploying Consoul as a production backend service with FastAPI, including multi-tenant isolation, security configuration, and observability.

## Quick Start

### Installation

```bash
# Core server dependencies
pip install consoul[server]

# With observability (Prometheus, OpenTelemetry, LangSmith)
pip install consoul[server,observability]
```

### Minimal Server

```python
from consoul.server import create_server

# Create server with environment-based config
app = create_server()

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Environment Configuration

```bash
# API Authentication
export CONSOUL_API_KEYS="your-api-key-1,your-api-key-2"

# Redis for sessions and rate limiting
export REDIS_URL="redis://localhost:6379"

# CORS (required for production)
export CONSOUL_CORS_ORIGINS="https://app.example.com,https://admin.example.com"

# Run server
uvicorn myapp:app --host 0.0.0.0 --port 8000
```

## Configuration Reference

### ServerConfig

The main configuration class combines all middleware settings:

```python
from consoul.server import create_server
from consoul.server.models import (
    ServerConfig,
    SecurityConfig,
    RateLimitConfig,
    CORSConfig,
    SessionConfig,
    ObservabilityConfig,
)

config = ServerConfig(
    host="0.0.0.0",
    port=8000,
    app_name="My API",
    security=SecurityConfig(...),
    rate_limit=RateLimitConfig(...),
    cors=CORSConfig(...),
    session=SessionConfig(...),
    observability=ObservabilityConfig(...),
)

app = create_server(config)
```

### SecurityConfig

API key authentication configuration.

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `CONSOUL_API_KEYS` | Comma-separated or JSON array of API keys | `[]` (disabled) |
| `CONSOUL_API_KEY_HEADER` | HTTP header name | `X-API-Key` |
| `CONSOUL_API_KEY_QUERY` | Query parameter name | `api_key` |
| `CONSOUL_BYPASS_PATHS` | Paths that bypass auth | `/health,/ready,/docs,/openapi.json` |

```python
SecurityConfig(
    api_keys=["key1", "key2"],
    header_name="X-API-Key",
    bypass_paths=["/health", "/ready"],
)
```

### RateLimitConfig

Rate limiting with optional Redis backend.

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `CONSOUL_DEFAULT_LIMITS` | Rate limits (semicolon-separated) | `10 per minute` |
| `CONSOUL_RATE_LIMIT_REDIS_URL` | Redis URL for distributed limiting | `None` |
| `REDIS_URL` | Universal fallback for Redis | `None` |
| `CONSOUL_STRATEGY` | Strategy: `fixed-window` or `moving-window` | `moving-window` |
| `CONSOUL_ENABLED` | Enable/disable rate limiting | `true` |

```python
RateLimitConfig(
    default_limits=["100 per hour", "10 per minute"],
    storage_url="redis://localhost:6379",
    strategy="moving-window",
)
```

### CORSConfig

Cross-Origin Resource Sharing configuration.

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `CONSOUL_CORS_ORIGINS` | Allowed origins (comma or JSON) | `*` |
| `CONSOUL_CORS_ALLOW_CREDENTIALS` | Allow credentials | `false` |
| `CONSOUL_CORS_ALLOW_METHODS` | Allowed methods | `*` |
| `CONSOUL_CORS_ALLOW_HEADERS` | Allowed headers | `*` |
| `CONSOUL_CORS_MAX_AGE` | Preflight cache duration (seconds) | `600` |

```python
CORSConfig(
    allowed_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
)
```

### SessionConfig

Session storage configuration.

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `CONSOUL_SESSION_REDIS_URL` | Redis URL for sessions | `None` |
| `REDIS_URL` | Universal fallback | `None` |
| `CONSOUL_SESSION_TTL` | Session TTL in seconds | `3600` (1 hour) |
| `CONSOUL_SESSION_KEY_PREFIX` | Redis key prefix | `consoul:session:` |

```python
SessionConfig(
    redis_url="redis://localhost:6379/1",
    ttl=7200,  # 2 hours
    key_prefix="myapp:session:",
)
```

### ObservabilityConfig

Metrics and tracing configuration.

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED` | Enable Prometheus metrics | `true` |
| `CONSOUL_OBSERVABILITY_METRICS_PORT` | Metrics server port | `9090` |
| `CONSOUL_OBSERVABILITY_OTEL_ENABLED` | Enable OpenTelemetry | `false` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTel collector endpoint | `None` |
| `CONSOUL_OBSERVABILITY_LANGSMITH_ENABLED` | Enable LangSmith | `false` |
| `LANGSMITH_API_KEY` | LangSmith API key | `None` |

```python
ObservabilityConfig(
    prometheus_enabled=True,
    metrics_port=9090,
    otel_enabled=True,
    otel_endpoint="http://jaeger:4317",
    langsmith_enabled=True,
)
```

## Multi-Tenant Isolation Patterns

### HTTP Pattern: Per-Request Sessions

Each HTTP request gets an isolated session that persists across requests:

```python
import redis
from consoul.sdk import create_session, restore_session, save_session_state
from consoul.sdk.session_store import RedisSessionStore

# Production: Use Redis for distributed sessions
redis_client = redis.from_url("redis://localhost:6379")
session_store = RedisSessionStore(
    redis_client=redis_client,
    ttl=3600,
)

@app.post("/chat")
async def chat(request: ChatRequest):
    # Load existing session or create new one
    state = session_store.load(request.session_id)

    if state:
        console = restore_session(state)
    else:
        console = create_session(
            session_id=request.session_id,
            model="gpt-4o-mini",
        )

    # Process message
    response = console.chat(request.message)

    # Save updated state
    new_state = save_session_state(console)
    session_store.save(request.session_id, new_state)

    return {"response": response}
```

### WebSocket Pattern: Per-Connection Sessions

WebSocket connections maintain session state for the connection lifetime:

```python
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # Create approval provider for tool execution
    approval_provider = WebSocketApprovalProvider(websocket, timeout=60.0)

    # One session per connection
    console = create_session(
        session_id=session_id,
        tools=["search", "web"],
        approval_provider=approval_provider,
    )

    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "message":
                response = console.chat(data["content"])
                await websocket.send_json({
                    "type": "response",
                    "content": response,
                })
    except WebSocketDisconnect:
        pass  # Session cleaned up automatically
```

### Session Locking for Concurrent Requests

Prevent race conditions when multiple requests hit the same session:

```python
from consoul.server.session_locks import SessionLock

# Lock manager is available on app.state
lock_manager = app.state.session_locks

async def chat_with_lock(session_id: str, message: str):
    async with SessionLock(lock_manager, session_id):
        # Atomic: load -> chat -> save
        state = await asyncio.to_thread(store.load, session_id)
        console = restore_session(state) if state else create_session(...)
        response = await asyncio.to_thread(console.chat, message)
        new_state = save_session_state(console)
        await asyncio.to_thread(store.save, session_id, new_state)
        return response
```

## Timeout Configuration

### Session TTL

```bash
# Environment variable
export CONSOUL_SESSION_TTL=7200  # 2 hours

# Or in code
SessionConfig(ttl=7200)
```

### WebSocket Tool Approval Timeout

```python
class WebSocketApprovalProvider:
    def __init__(self, websocket: WebSocket, timeout: float = 60.0):
        self.timeout = timeout

    async def on_tool_request(self, request: ToolRequest) -> bool:
        # Send approval request
        await self.websocket.send_json({
            "type": "tool_request",
            "id": request.id,
            "name": request.name,
        })

        # Wait with timeout
        try:
            approved = await asyncio.wait_for(
                self._pending[request.id],
                timeout=self.timeout
            )
            return approved
        except asyncio.TimeoutError:
            return False  # Deny on timeout
```

### Rate Limit Windows

```bash
# Multiple rate limits
export CONSOUL_DEFAULT_LIMITS="10/minute;100/hour;1000/day"
```

## Security Best Practices

### 1. API Key Authentication

```bash
# Never hardcode - use environment variables
export CONSOUL_API_KEYS="$(openssl rand -hex 32)"
```

### 2. CORS Configuration

```bash
# Production: Specific origins only
export CONSOUL_CORS_ORIGINS="https://app.example.com,https://admin.example.com"

# Never use wildcards in production
# CONSOUL_CORS_ORIGINS="*"  # INSECURE
```

### 3. Rate Limiting with Redis

```bash
# Distributed rate limiting prevents bypass via multiple instances
export CONSOUL_RATE_LIMIT_REDIS_URL="redis://localhost:6379"
export CONSOUL_DEFAULT_LIMITS="30/minute"
```

### 4. Input Validation

All request models use Pydantic validation:

```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=10000)
    model: str | None = Field(None, pattern=r"^[a-z0-9-]+$")
```

### 5. Safe Session Serialization

Sessions are serialized as JSON (never pickle) to prevent RCE:

```python
from consoul.sdk import save_session_state, restore_session

# Safe: JSON-based serialization
state = save_session_state(console)  # Returns dict
session_store.save(session_id, state)

# Restore
state = session_store.load(session_id)
console = restore_session(state)
```

## Observability Setup

### Prometheus Metrics

Metrics are served on a separate port (default: 9090):

```bash
export CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED=true
export CONSOUL_OBSERVABILITY_METRICS_PORT=9090
```

Available metrics:
- `consoul_request_total` - Request count by endpoint, method, status, model
- `consoul_request_latency_seconds` - Request latency histogram
- `consoul_token_usage_total` - Token usage by direction, model, session
- `consoul_active_sessions` - Gauge of active sessions
- `consoul_tool_executions_total` - Tool execution count by name, status
- `consoul_errors_total` - Error count by endpoint, error type

### OpenTelemetry Tracing

```bash
export CONSOUL_OBSERVABILITY_OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT="http://jaeger:4317"
export CONSOUL_OBSERVABILITY_OTEL_SERVICE_NAME="consoul-api"
```

### LangSmith Integration

```bash
export CONSOUL_OBSERVABILITY_LANGSMITH_ENABLED=true
export LANGSMITH_API_KEY="ls_..."
```

### Health Check Endpoints

Built-in endpoints (exempt from auth/rate limiting):

```bash
# Liveness probe
curl http://localhost:8000/health
# {"status":"ok","service":"Consoul API","version":"0.4.2","timestamp":"..."}

# Readiness probe (checks Redis)
curl http://localhost:8000/ready
# {"status":"ready","checks":{"redis":true},"timestamp":"..."}
```

## Production Deployment Checklist

### Required Configuration

- [ ] `CONSOUL_API_KEYS` - Set secure API keys
- [ ] `CONSOUL_CORS_ORIGINS` - Specific origins (no wildcards)
- [ ] `REDIS_URL` - Redis for sessions and rate limiting
- [ ] `CONSOUL_DEFAULT_LIMITS` - Appropriate rate limits

### Security

- [ ] HTTPS/TLS termination (via reverse proxy)
- [ ] API keys stored securely (not in code)
- [ ] CORS configured for specific origins
- [ ] Rate limiting enabled with Redis backend
- [ ] Input validation on all endpoints

### Scaling

- [ ] Redis for distributed sessions
- [ ] Redis for distributed rate limiting
- [ ] Health check endpoints configured in load balancer
- [ ] Horizontal scaling with stateless instances

### Monitoring

- [ ] Prometheus metrics enabled
- [ ] Health/readiness probes configured
- [ ] Error alerting configured
- [ ] Token usage monitoring

### Example Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
      - "9090:9090"  # Metrics
    environment:
      - REDIS_URL=redis://redis:6379
      - CONSOUL_API_KEYS=${API_KEYS}
      - CONSOUL_CORS_ORIGINS=https://app.example.com
      - CONSOUL_DEFAULT_LIMITS=30/minute;500/hour
      - CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED=true
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

## Troubleshooting

### Common Issues

**API keys not working**
```bash
# Verify format (comma-separated)
echo $CONSOUL_API_KEYS
# Check header name
curl -H "X-API-Key: your-key" http://localhost:8000/chat
```

**Rate limiting not distributed**
```bash
# Ensure Redis URL is set
echo $CONSOUL_RATE_LIMIT_REDIS_URL
# Or universal fallback
echo $REDIS_URL
```

**Sessions not persisting**
```bash
# Check Redis connection
redis-cli -u $REDIS_URL ping
# Check TTL
echo $CONSOUL_SESSION_TTL
```

**CORS errors**
```bash
# Verify allowed origins include your frontend
echo $CONSOUL_CORS_ORIGINS
# Check browser console for specific origin errors
```

### Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
# CONSOUL_LOG_LEVEL=DEBUG
```

## See Also

- [Examples: Backend SDK](../examples/sdk/backend/README.md)
- [API Reference: Server Models](../api/server-models.md)
- [Security Considerations](../examples/README.md#security-considerations)
