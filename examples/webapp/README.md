# Consoul Web App Example

A minimal chat web app using Consoul as the backend.

## Quick Start

1. **Set your API key:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   # or
   export OPENAI_API_KEY="sk-..."
   ```

2. **Run the server:**
   ```bash
   cd examples/webapp
   python server.py
   ```

3. **Open in browser:**
   ```
   http://localhost:8000
   ```

## Features

- WebSocket streaming for real-time responses
- Session persistence (conversation memory)
- Auto-reconnection on disconnect
- Tool approval support (auto-approved in demo)

## Configuration

Set environment variables to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `CONSOUL_API_KEYS` | - | Require API key auth |
| `CONSOUL_DEFAULT_LIMITS` | 30/min | Rate limiting |

## Architecture

```
┌─────────────┐     WebSocket      ┌─────────────┐
│   Browser   │ ◄──────────────────►│   Server    │
│  index.html │    /ws/chat/{id}   │  server.py  │
└─────────────┘                    └──────┬──────┘
                                          │
                                   ┌──────▼──────┐
                                   │   Consoul   │
                                   │  (LangChain)│
                                   └──────┬──────┘
                                          │
                                   ┌──────▼──────┐
                                   │  LLM API    │
                                   │ (OpenAI/    │
                                   │  Anthropic) │
                                   └─────────────┘
```

## Production Notes

For production deployments:
- Use HTTPS (TLS termination via reverse proxy)
- Set `CONSOUL_API_KEYS` for authentication
- Configure Redis for session storage
- See [Backend Deployment Guide](../../docs/backend-deployment.md)
