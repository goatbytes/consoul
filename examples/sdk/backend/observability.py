#!/usr/bin/env python3
"""Observability Example - Prometheus, OpenTelemetry, LangSmith.

Demonstrates production monitoring and tracing setup:
- Prometheus metrics on separate port (:9090)
- OpenTelemetry distributed tracing
- LangSmith LLM tracing

Usage:
    # Install observability dependencies
    pip install consoul[server,observability]

    # For Prometheus only
    pip install consoul[server,prometheus]

    # Run with default config (Prometheus enabled)
    python examples/sdk/backend/observability.py

    # Access metrics
    curl http://localhost:9090/metrics

    # Enable OpenTelemetry
    export CONSOUL_OBSERVABILITY_OTEL_ENABLED=true
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

    # Enable LangSmith
    export CONSOUL_OBSERVABILITY_LANGSMITH_ENABLED=true
    export LANGSMITH_API_KEY=ls_...
"""

from consoul.server import create_server
from consoul.server.models import ObservabilityConfig, ServerConfig


def create_observability_config() -> ServerConfig:
    """Create server config with full observability."""
    return ServerConfig(
        app_name="Observable Consoul API",
        observability=ObservabilityConfig(
            # Prometheus metrics on separate port
            prometheus_enabled=True,
            metrics_port=9090,
            # OpenTelemetry (requires env vars)
            otel_enabled=False,  # Enable via CONSOUL_OBSERVABILITY_OTEL_ENABLED
            otel_service_name="consoul-api",
            # LangSmith (requires LANGSMITH_API_KEY)
            langsmith_enabled=False,  # Enable via CONSOUL_OBSERVABILITY_LANGSMITH_ENABLED
        ),
    )


# Create app with observability config
app = create_server(create_observability_config())


if __name__ == "__main__":
    import os

    import uvicorn

    print("=" * 60)
    print("Observability Example")
    print("=" * 60)
    print()
    print("Metrics:")
    print("  Prometheus: http://localhost:9090/metrics")
    print()
    print("Available metrics:")
    print("  - consoul_request_total")
    print("  - consoul_request_latency_seconds")
    print("  - consoul_token_usage_total")
    print("  - consoul_active_sessions")
    print("  - consoul_tool_executions_total")
    print("  - consoul_errors_total")
    print()
    print("Tracing:")
    otel = os.environ.get("CONSOUL_OBSERVABILITY_OTEL_ENABLED", "false")
    langsmith = os.environ.get("CONSOUL_OBSERVABILITY_LANGSMITH_ENABLED", "false")
    print(f"  OpenTelemetry: {otel}")
    print(f"  LangSmith: {langsmith}")
    print()
    print("Enable tracing:")
    print("  export CONSOUL_OBSERVABILITY_OTEL_ENABLED=true")
    print("  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317")
    print()
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
