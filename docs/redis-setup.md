# Redis Setup Guide

Minimal guide for setting up Redis with Consoul.

## Installation

### macOS (Homebrew)

```bash
brew install redis
brew services start redis
```

### Ubuntu/Debian

```bash
sudo apt update && sudo apt install redis-server
sudo systemctl enable redis-server --now
```

### Docker (One-liner)

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

## Verify Installation

```bash
redis-cli ping
# Expected: PONG
```

## Consoul Integration

### Environment Variable

```bash
export REDIS_URL="redis://localhost:6379"
```

### Session Storage

```python
import redis
from consoul.sdk.session_store import RedisSessionStore

client = redis.from_url("redis://localhost:6379")
session_store = RedisSessionStore(redis_client=client, ttl=3600)
```

### Rate Limiting

```bash
export CONSOUL_RATE_LIMIT_REDIS_URL="redis://localhost:6379"
export CONSOUL_DEFAULT_LIMITS="30/minute;500/hour"
```

## Common Commands

| Command | Description |
|---------|-------------|
| `redis-cli ping` | Test connection |
| `redis-cli info` | Server information |
| `redis-cli keys "consoul:*"` | List Consoul keys |
| `redis-cli flushdb` | Clear current database |
| `redis-cli monitor` | Watch commands in real-time |

## Service Management

### macOS

```bash
brew services start redis    # Start
brew services stop redis     # Stop
brew services restart redis  # Restart
```

### Linux (systemd)

```bash
sudo systemctl start redis-server
sudo systemctl stop redis-server
sudo systemctl restart redis-server
```

### Docker

```bash
docker start redis
docker stop redis
docker logs redis
```

## Troubleshooting

### Connection Refused

```bash
# Check if Redis is running
redis-cli ping

# macOS: Start service
brew services start redis

# Linux: Check status
sudo systemctl status redis-server
```

### Wrong Database

Redis has 16 databases (0-15). Use different databases for different purposes:

```bash
export CONSOUL_SESSION_REDIS_URL="redis://localhost:6379/1"  # DB 1 for sessions
export CONSOUL_RATE_LIMIT_REDIS_URL="redis://localhost:6379/2"  # DB 2 for rate limits
```

### Authentication Required

```bash
# With password
export REDIS_URL="redis://:yourpassword@localhost:6379"

# Test connection
redis-cli -a yourpassword ping
```

### Clear Test Data

```bash
# Clear all Consoul session keys
redis-cli keys "consoul:session:*" | xargs redis-cli del

# Or flush entire database (caution in production)
redis-cli flushdb
```

## Production Considerations

- Use Redis 7+ for best performance
- Enable persistence (`appendonly yes` in redis.conf)
- Set `maxmemory` and eviction policy
- Use TLS for remote connections
- Consider Redis Sentinel or Cluster for HA

See [Backend Deployment Guide](backend-deployment.md) for production configuration.
