#!/bin/bash
# Consoul API Server Entrypoint
# Configurable via environment variables

set -e

# Configuration with defaults
HOST="${CONSOUL_HOST:-0.0.0.0}"
PORT="${CONSOUL_PORT:-8000}"
WORKERS="${CONSOUL_WORKERS:-1}"
LOG_LEVEL="${CONSOUL_LOG_LEVEL:-info}"

# Log startup information
echo "========================================"
echo "  Consoul API Server"
echo "========================================"
echo "Host:      $HOST"
echo "Port:      $PORT"
echo "Workers:   $WORKERS"
echo "Log Level: $LOG_LEVEL"
echo "========================================"

# Optional: Wait for Redis if configured
if [ -n "$REDIS_URL" ] || [ -n "$CONSOUL_SESSION_REDIS_URL" ]; then
    REDIS_HOST=$(echo "${REDIS_URL:-$CONSOUL_SESSION_REDIS_URL}" | sed -E 's|redis://([^:@]+).*|\1|')
    echo "Waiting for Redis at $REDIS_HOST..."
    for i in {1..30}; do
        if nc -z "$REDIS_HOST" 6379 2>/dev/null; then
            echo "Redis is available!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "Warning: Redis not available after 30 attempts, starting anyway..."
        fi
        sleep 1
    done
fi

# Start the server using the factory pattern
exec uvicorn \
    "consoul.server:create_server" \
    --factory \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    --access-log
