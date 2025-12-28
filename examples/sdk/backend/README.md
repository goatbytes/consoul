# Backend Examples

Production-ready backend examples using the Consoul server module.

## Prerequisites

```bash
pip install consoul[server]

# With observability (optional)
pip install consoul[server,observability]
```

## Examples

| Example | Description |
|---------|-------------|
| [basic_server.py](basic_server.py) | Minimal server using factory pattern |
| [multi_tenant_http.py](multi_tenant_http.py) | HTTP session isolation pattern |
| [multi_tenant_websocket.py](multi_tenant_websocket.py) | WebSocket per-connection sessions |
| [security_config.py](security_config.py) | Full security middleware setup |
| [observability.py](observability.py) | Prometheus, OpenTelemetry, LangSmith |

## Running Examples

```bash
# Basic server
python examples/sdk/backend/basic_server.py

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Configuration

All examples support environment-based configuration:

```bash
# API authentication
export CONSOUL_API_KEYS="your-key-here"

# Redis for sessions and rate limiting
export REDIS_URL="redis://localhost:6379"

# CORS (production)
export CONSOUL_CORS_ORIGINS="https://app.example.com"
```

## Documentation

- [Backend Deployment Guide](../../../docs/backend-deployment.md)
- [Security Considerations](../../README.md#security-considerations)
