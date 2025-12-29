# Multi-stage Dockerfile for Consoul API Server
# Optimized for production deployment on GCP, AWS, and Azure

# =============================================================================
# Stage 1: Builder - Install dependencies and build wheels
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry for dependency management
RUN pip install --no-cache-dir poetry==1.8.3

# Copy dependency files first (better layer caching)
COPY pyproject.toml poetry.lock* ./

# Export requirements and build wheels
# Include server and observability extras for production
RUN poetry config virtualenvs.create false \
    && poetry export -f requirements.txt --extras server --extras observability --without-hashes -o requirements.txt \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# =============================================================================
# Stage 2: Production - Minimal runtime image
# =============================================================================
FROM python:3.12-slim AS production

# Create non-root user for security
RUN groupadd --gid 1000 consoul \
    && useradd --uid 1000 --gid consoul --shell /bin/bash --create-home consoul

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels requirements.txt

# Copy application source code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the consoul package (editable mode for faster startup)
RUN pip install --no-cache-dir -e ".[server,observability]"

# Copy entrypoint script
COPY deployment/cloud/shared/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set ownership to non-root user
RUN chown -R consoul:consoul /app

# Switch to non-root user
USER consoul

# Environment defaults
ENV CONSOUL_HOST=0.0.0.0
ENV CONSOUL_PORT=8000
ENV CONSOUL_WORKERS=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose ports
# 8000 - API server
# 9090 - Prometheus metrics
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
