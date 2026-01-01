# Consoul Performance Tuning Guide

Comprehensive guide for tuning connection pools, thread pools, and server parameters for optimal Consoul performance under load.

## Table of Contents

- [Overview](#overview)
- [Redis Connection Pool](#redis-connection-pool)
- [HTTP Connection Limits (LLM Providers)](#http-connection-limits-llm-providers)
- [WebSocket Connection Management](#websocket-connection-management)
- [Thread Pool Sizing](#thread-pool-sizing)
- [Uvicorn Worker Configuration](#uvicorn-worker-configuration)
- [Circuit Breaker Tuning](#circuit-breaker-tuning)
- [Session Garbage Collection](#session-garbage-collection)
- [Prometheus Metrics](#prometheus-metrics)
- [Quick Reference](#quick-reference)

---

## Overview

### Connection Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Consoul Connection Flow                              │
│                                                                             │
│  Client                                                                     │
│    │                                                                        │
│    ├──── HTTP/WS ─────┐                                                     │
│    │                  ▼                                                     │
│    │            ┌──────────────┐                                            │
│    │            │   Uvicorn    │ ◀── Workers, Concurrency, Backlog          │
│    │            │   Workers    │                                            │
│    │            └──────┬───────┘                                            │
│    │                   │                                                    │
│    │      ┌────────────┼────────────┐                                       │
│    │      ▼            ▼            ▼                                       │
│    │ ┌─────────┐ ┌──────────┐ ┌──────────────┐                              │
│    │ │Rate     │ │Session   │ │ LLM Provider │                              │
│    │ │Limiter  │ │Store     │ │ HTTP Clients │                              │
│    │ └────┬────┘ └────┬─────┘ └──────┬───────┘                              │
│    │      │           │              │                                       │
│    │      ▼           ▼              ▼                                       │
│    │ ┌──────────────────────┐  ┌───────────────┐                            │
│    │ │    Redis Pool        │  │ httpx Pool    │                            │
│    │ │  (Session + Limits)  │  │ (per provider)│                            │
│    │ └──────────────────────┘  └───────────────┘                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Bottlenecks

| Component | Symptom | Tuning Target |
|-----------|---------|---------------|
| Redis | Connection timeouts, rate limit errors | Redis server limits, fallback mode |
| HTTP Pool | LLM request delays, connection refused | Provider SDK settings |
| WebSocket | Slow client disconnections | Backpressure (code constants) |
| Thread Pool | Blocking during Redis ops | asyncio defaults |
| Uvicorn | Request queuing, 503 errors | Workers, limit-concurrency |

### Prerequisites

- **Redis**: Required for distributed rate limiting and session storage
- **Prometheus**: Recommended for monitoring pool utilization
- **Load Testing Tool**: k6, locust, or wrk for baseline establishment

---

## Redis Connection Pool

Consoul uses Redis for two critical functions, each with separate connection pools for isolation.

### Session Storage

Stores conversation state across requests:

```bash
# Redis URL for session storage
CONSOUL_SESSION_REDIS_URL=redis://redis:6379/0

# Session TTL (seconds, default: 3600)
CONSOUL_SESSION_TTL=3600

# Key prefix for namespacing
CONSOUL_SESSION_KEY_PREFIX=consoul:session
```

### Rate Limiting

Enforces request limits across distributed instances:

```bash
# Separate Redis database/instance for isolation
CONSOUL_RATE_LIMIT_REDIS_URL=redis://redis:6379/1

# Key prefix for rate limit buckets
CONSOUL_RATE_LIMIT_KEY_PREFIX=consoul:ratelimit
```

### Connection Pool Parameters

The default redis-py pool is effectively unlimited, which can overwhelm Redis under load.
Consoul uses the redis-py library defaults. To customize pool settings, you would need to
modify the application code or configure Redis server-side limits.

**redis-py defaults**:
- `max_connections`: 2^31 (effectively unlimited)
- `socket_timeout`: None (blocking forever)
- `socket_connect_timeout`: None (blocking forever)

**Redis server-side limits** (recommended):
```bash
# In redis.conf or via command line
maxclients 10000
timeout 300
tcp-keepalive 300
```

### Resilient Fallback (Graceful Degradation)

Consoul supports automatic fallback to in-memory storage when Redis is unavailable:

```bash
# Enable fallback to in-memory storage
CONSOUL_REDIS_FALLBACK_ENABLED=true

# Reconnection attempt interval (seconds, range: 10-3600)
CONSOUL_REDIS_RECONNECT_INTERVAL=60
```

When in fallback mode:
- Sessions are stored in-memory (not shared across instances)
- Rate limiting uses in-memory counters (limits enforced per-instance)
- Metric `consoul_redis_degraded=1` indicates degraded state
- Automatic recovery when Redis becomes available

### Sizing Guidelines

| Concurrent Users | max_connections | Notes |
|-----------------|-----------------|-------|
| < 100 | 20 | Small deployments |
| 100-500 | 50 | Medium traffic |
| 500-2000 | 100 | High traffic |
| > 2000 | 200+ | Consider Redis Cluster |

---

## HTTP Connection Limits (LLM Providers)

LLM provider SDKs (OpenAI, Anthropic) use httpx internally for HTTP connections.
These are managed by the provider SDKs and LiteLLM, not directly configurable via
Consoul environment variables.

### Default Connection Pools

```
OpenAI SDK:
  └── httpx.AsyncClient
      ├── max_connections: 100 (per host)
      └── max_keepalive_connections: 20

Anthropic SDK:
  └── httpx.AsyncClient
      ├── max_connections: 100 (per host)
      └── max_keepalive_connections: 20
```

### Provider SDK Configuration

Provider timeouts can be configured via their respective environment variables
(handled by the SDK, not Consoul):

```bash
# OpenAI SDK timeout (seconds) - read by openai-python
OPENAI_TIMEOUT=120

# Anthropic SDK timeout (seconds) - read by anthropic-python
ANTHROPIC_TIMEOUT=120
```

> **Note**: These are provider SDK environment variables, not Consoul-specific.
> Refer to each provider's documentation for available configuration options.

### Rate Limit Handling

When provider rate limits are hit, the circuit breaker prevents cascade failures:

```
Provider Rate Limit → Circuit Breaker OPEN → Fast-fail locally → Retry after cooldown
```

---

## WebSocket Connection Management

### Connection Manager

Consoul tracks active WebSocket connections with a thread-safe counter:

```python
# From websocket.py
class WebSocketConnectionManager:
    """Tracks active WebSocket connections."""

    @property
    def active_count(self) -> int:
        """Returns current active connection count."""
```

### Backpressure Handling

Prevents slow clients from consuming server resources:

```python
class BackpressureHandler:
    MAX_BUFFER_SIZE = 1000      # Maximum tokens to buffer
    SEND_TIMEOUT = 5.0          # Timeout per message send (seconds)
```

**Behavior**:
1. Tokens queued in asyncio.Queue (max 1000)
2. 5-second timeout per message send
3. Slow clients disconnected with code 1008 (Policy Violation)
4. Prevents DoS from intentionally slow consumers

### Load Balancer Configuration

Configure at load balancer level for global limits:

**NGINX**:
```nginx
# Maximum WebSocket connections
worker_connections 10000;

# WebSocket upgrade
location /ws/ {
    proxy_pass http://consoul-backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # Idle timeout
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
```

**AWS ALB**:
```yaml
# Application Load Balancer settings
idle_timeout: 300          # WebSocket idle timeout (seconds)
target_group:
  deregistration_delay: 60 # Graceful shutdown time
```

### Proposed Environment Variables

```bash
# Maximum WebSocket connections per instance (future)
CONSOUL_MAX_WEBSOCKET_CONNECTIONS=10000

# Idle timeout for inactive WebSocket connections (future)
CONSOUL_WEBSOCKET_IDLE_TIMEOUT=300
```

---

## Thread Pool Sizing

### Default Thread Pool

Python's asyncio uses a ThreadPoolExecutor for `asyncio.to_thread()`:

```python
# Default size
max_workers = min(32, os.cpu_count() + 4)
# Example: 8-core machine → min(32, 8+4) = 12 workers
```

### Usage in Consoul

Thread pool is used for blocking operations:

| Operation | Location | Frequency |
|-----------|----------|-----------|
| Redis session load | `factory.py:820` | Per request |
| Redis session save | `factory.py:844` | Per response |
| Session cleanup | `factory.py:344` | Every GC interval |
| Chat execution | `factory.py:838` | Per message |

### Increasing Thread Pool Size

For I/O-heavy workloads, the default asyncio thread pool can be increased at the
application level. This requires code modification as there is no environment
variable currently implemented for this.

**Code example** (if customizing Consoul):
```python
# At application startup
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Create larger pool
executor = ThreadPoolExecutor(max_workers=100)

# Set as default for asyncio.to_thread()
loop = asyncio.get_event_loop()
loop.set_default_executor(executor)
```

> **Note**: Thread pool sizing is not currently configurable via environment
> variables. The default asyncio pool (`min(32, cpu_count + 4)`) is typically
> sufficient for most deployments.

### Sizing Guidelines

| Workload | Thread Pool Size | Rationale |
|----------|------------------|-----------|
| Light I/O | 20 | Default is usually sufficient |
| Moderate I/O | 50 | Multiple Redis ops per request |
| Heavy I/O | 100 | High concurrency, slow backends |
| Extreme | 200+ | Consider async alternatives |

---

## Uvicorn Worker Configuration

### Production Command

```bash
uvicorn consoul.server:create_server \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \                    # Number of worker processes
  --loop uvloop \                  # High-performance event loop
  --http httptools \               # Fast HTTP parser
  --limit-concurrency 1000 \       # Max concurrent connections
  --timeout-keep-alive 30 \        # Keep-alive timeout (seconds)
  --backlog 2048 \                 # Connection queue size
  --access-log \                   # Enable access logging
  --log-level info
```

### Worker Sizing

| CPU Cores | Workers | Notes |
|-----------|---------|-------|
| 1 | 2 | Minimum for production |
| 2 | 4 | Small instance |
| 4 | 8-12 | Medium instance |
| 8 | 16-24 | Large instance |
| 16+ | 32-48 | High-traffic deployment |

**Formula**: `workers = 2-3 × cpu_cores`

### Key Parameters

| Parameter | Default | Recommended | Description |
|-----------|---------|-------------|-------------|
| `--workers` | 1 | 2-4× cores | Worker processes |
| `--loop` | asyncio | uvloop | Event loop implementation |
| `--http` | auto | httptools | HTTP parser |
| `--limit-concurrency` | None | 1000 | Max concurrent connections |
| `--timeout-keep-alive` | 5 | 30 | Keep-alive timeout |
| `--backlog` | 2048 | 2048 | Listen queue size |

### Gunicorn Alternative

For more advanced process management:

```bash
gunicorn consoul.server:create_server \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 \
  --graceful-timeout 60 \
  --keep-alive 30 \
  --max-requests 10000 \           # Restart workers after N requests
  --max-requests-jitter 1000       # Randomize restart timing
```

---

## Circuit Breaker Tuning

The circuit breaker prevents cascade failures when LLM providers are unavailable.

### State Diagram

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │   CLOSED ─────(5 failures)─────▶ OPEN                          │
    │     ▲                              │                            │
    │     │                              │                            │
    │     │                        (60s timeout)                      │
    │     │                              │                            │
    │     │                              ▼                            │
    │   (3 successes)◀──────────── HALF_OPEN ────(any failure)───┐   │
    │                                                             │   │
    │                                    ▲                        │   │
    │                                    └────────────────────────┘   │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
```

### Environment Variables

```bash
# Enable/disable circuit breaker
CONSOUL_CIRCUIT_BREAKER_ENABLED=true

# Failures before opening circuit
CONSOUL_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5

# Successes to close circuit
CONSOUL_CIRCUIT_BREAKER_SUCCESS_THRESHOLD=3

# Seconds before half-open transition
CONSOUL_CIRCUIT_BREAKER_TIMEOUT=60

# Max test requests in half-open state
CONSOUL_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS=3
```

### Tuning Guidelines

| Scenario | failure_threshold | timeout | Notes |
|----------|-------------------|---------|-------|
| Sensitive | 3 | 30 | Quick protection |
| Balanced | 5 | 60 | Default settings |
| Resilient | 10 | 120 | Tolerate transient errors |

### Monitoring

```promql
# Circuit breaker state by provider
consoul_circuit_breaker_state{provider="openai"}

# Trip count (indicates instability)
increase(consoul_circuit_breaker_trips_total[1h])

# Rejection rate (users affected)
rate(consoul_circuit_breaker_rejections_total[5m])
```

---

## Session Garbage Collection

### Configuration

```bash
# GC interval (seconds, default: 3600 = 1 hour)
CONSOUL_SESSION_GC_INTERVAL=3600

# Keys processed per GC cycle (default: 100)
CONSOUL_SESSION_GC_BATCH_SIZE=100
```

### How It Works

1. Background task runs every `gc_interval` seconds
2. Uses Redis SCAN (non-blocking) to find expired keys
3. Deletes `batch_size` keys per cycle
4. Runs in thread pool to avoid blocking event loop

### Tuning for High-Volume Deployments

| Sessions/hour | gc_interval | batch_size | Notes |
|---------------|-------------|------------|-------|
| < 1000 | 3600 | 100 | Default settings |
| 1000-10000 | 1800 | 200 | More frequent cleanup |
| > 10000 | 900 | 500 | Aggressive cleanup |

### Memory Considerations

```bash
# Session TTL affects memory usage
# Shorter TTL = less memory, more reloads
CONSOUL_SESSION_TTL=1800  # 30 minutes for lower memory

# Longer TTL = more memory, better UX
CONSOUL_SESSION_TTL=7200  # 2 hours for persistent sessions
```

---

## Prometheus Metrics

### Performance Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `consoul_request_latency_seconds` | Histogram | Request latency distribution |
| `consoul_request_total` | Counter | Total requests by endpoint/status |
| `consoul_active_sessions` | Gauge | Current active session count |
| `consoul_token_usage_total` | Counter | Tokens consumed by model |

### Connection Pool Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `consoul_redis_degraded` | Gauge | 1 if Redis in fallback mode |
| `consoul_redis_recovered_total` | Counter | Redis recovery events |

### Circuit Breaker Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `consoul_circuit_breaker_state` | Gauge | 0=closed, 1=half-open, 2=open |
| `consoul_circuit_breaker_trips_total` | Counter | Circuit open events |
| `consoul_circuit_breaker_rejections_total` | Counter | Rejected requests |

### Example Grafana Dashboard Queries

```promql
# P99 latency
histogram_quantile(0.99, sum(rate(consoul_request_latency_seconds_bucket[5m])) by (le))

# Request rate by status
sum(rate(consoul_request_total[5m])) by (status)

# Active sessions trend
consoul_active_sessions

# Redis health
consoul_redis_degraded == 1
```

### Alerting Rules

```yaml
groups:
  - name: consoul-performance
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.99, sum(rate(consoul_request_latency_seconds_bucket[5m])) by (le)) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P99 latency exceeds 5 seconds"

      - alert: RedisUnavailable
        expr: consoul_redis_degraded == 1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Redis unavailable, running in degraded mode"

      - alert: CircuitBreakerOpen
        expr: consoul_circuit_breaker_state == 2
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.provider }}"
```

---

## Quick Reference

### Consoul Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| **Redis** | | |
| `CONSOUL_SESSION_REDIS_URL` | None | Session storage Redis URL |
| `CONSOUL_RATE_LIMIT_REDIS_URL` | None | Rate limiter Redis URL |
| `REDIS_URL` | None | Universal Redis fallback |
| `CONSOUL_REDIS_FALLBACK_ENABLED` | false | Enable in-memory fallback |
| `CONSOUL_REDIS_RECONNECT_INTERVAL` | 60 | Reconnection interval (seconds) |
| **Circuit Breaker** | | |
| `CONSOUL_CIRCUIT_BREAKER_ENABLED` | true | Enable circuit breaker |
| `CONSOUL_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | 5 | Failures before open |
| `CONSOUL_CIRCUIT_BREAKER_SUCCESS_THRESHOLD` | 3 | Successes to close |
| `CONSOUL_CIRCUIT_BREAKER_TIMEOUT` | 60 | Seconds before half-open |
| `CONSOUL_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS` | 3 | Test calls in half-open |
| **Session** | | |
| `CONSOUL_SESSION_TTL` | 3600 | Session TTL (seconds) |
| `CONSOUL_SESSION_KEY_PREFIX` | consoul:session: | Redis key prefix |
| `CONSOUL_SESSION_GC_INTERVAL` | 3600 | GC interval (seconds) |
| `CONSOUL_SESSION_GC_BATCH_SIZE` | 100 | Keys per GC cycle |
| **Rate Limiting** | | |
| `CONSOUL_RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `CONSOUL_DEFAULT_LIMITS` | 10/minute | Default rate limits |
| `CONSOUL_KEY_PREFIX` | consoul:ratelimit | Rate limit Redis key prefix |

### Production Checklist

- [ ] Redis URLs configured for session and rate limiting
- [ ] Redis fallback enabled (`CONSOUL_REDIS_FALLBACK_ENABLED=true`)
- [ ] Uvicorn workers set to 2-4× CPU cores
- [ ] Circuit breaker enabled for LLM providers
- [ ] Prometheus metrics enabled and scraped
- [ ] Alert rules configured for latency and availability
- [ ] Session TTL and GC tuned for memory constraints
- [ ] Load tested with expected traffic patterns

---

## Related Documentation

- [Scaling Guide](../operations/scaling-guide.md) - Horizontal and vertical scaling
- [Security Checklist](../operations/security-checklist.md) - Security configuration
- [Runbook](../operations/runbook.md) - Day-to-day operations

---

**Last Updated**: December 2025
**Version**: 1.0
**Ticket**: SOUL-344
