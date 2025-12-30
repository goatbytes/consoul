# Consoul Legal Industry Server
# Production-ready Docker image for legal AI deployment
#
# Security features:
# - Non-root user with fixed UID/GID for volume compatibility
# - Minimal base image
# - Health check
# - Read-only filesystem (where possible)

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY examples/legal/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Security: Create non-root user with fixed UID/GID for volume permissions
# Using 1000:1000 which is common for first non-root user
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} consoul && useradd -u ${UID} -g consoul -m consoul

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder
COPY --from=builder /root/.local /home/consoul/.local

# Set Python path
ENV PATH=/home/consoul/.local/bin:$PATH
ENV PYTHONPATH=/app

# Create application directories with correct ownership
WORKDIR /app
RUN mkdir -p /data/matters /var/log/consoul \
    && chown -R consoul:consoul /app /data /var/log/consoul

# Copy application code (build context is repo root per docker-compose.yml)
COPY --chown=consoul:consoul . /app/

# Install gosu for dropping privileges in entrypoint (su-exec is Alpine-only)
RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && gosu nobody true  # Verify gosu works

# Create entrypoint script to fix volume permissions on startup
# This runs as root, fixes permissions, then execs as consoul user
RUN printf '#!/bin/sh\n\
# Fix ownership of mounted volumes (they may be created as root)\n\
chown -R consoul:consoul /data/matters /var/log/consoul 2>/dev/null || true\n\
# Drop privileges and run the application\n\
exec gosu consoul "$@"\n' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Environment variables (override in docker-compose or deployment)
ENV PYTHONUNBUFFERED=1
ENV CONSOUL_LOG_LEVEL=INFO

# Use entrypoint to fix permissions before dropping to non-root
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "examples.legal.server"]
