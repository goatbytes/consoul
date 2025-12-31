"""Observability module for Consoul server.

Provides production-grade observability integrations:
- Prometheus metrics on separate port
- LangSmith LLM tracing
- OpenTelemetry distributed tracing

All integrations are optional and gracefully degrade if packages not installed.

Example:
    >>> from consoul.server.observability import MetricsCollector, start_metrics_server
    >>> from consoul.server.observability import setup_langsmith, setup_opentelemetry
    >>>
    >>> # Start Prometheus metrics server on port 9090
    >>> start_metrics_server(9090)
    >>> metrics = MetricsCollector()
    >>>
    >>> # Setup LangSmith (requires LANGSMITH_API_KEY env var)
    >>> tracer = setup_langsmith()
    >>>
    >>> # Setup OpenTelemetry (requires OTEL_EXPORTER_OTLP_ENDPOINT env var)
    >>> setup_opentelemetry(service_name="consoul", endpoint="http://localhost:4317")

Installation:
    pip install consoul[observability]  # All integrations
    pip install consoul[prometheus]     # Prometheus only
    pip install consoul[langsmith]      # LangSmith only
    pip install consoul[otel]           # OpenTelemetry only
"""

from consoul.server.observability.metrics import (
    MetricsCollector,
    create_app_state_metrics_middleware,
    create_metrics_middleware,
    start_metrics_server,
)
from consoul.server.observability.tracing import setup_langsmith, setup_opentelemetry

__all__ = [
    "MetricsCollector",
    "create_app_state_metrics_middleware",
    "create_metrics_middleware",
    "setup_langsmith",
    "setup_opentelemetry",
    "start_metrics_server",
]
