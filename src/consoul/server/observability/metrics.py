"""Prometheus metrics collection for Consoul server.

Provides MetricsCollector for recording request metrics, token usage,
tool executions, and errors. Runs on a separate port (default 9090)
following Kubernetes/Prometheus best practices.

Gracefully degrades if prometheus-client is not installed.

Example:
    >>> from consoul.server.observability.metrics import MetricsCollector, start_metrics_server
    >>>
    >>> # Start metrics server on separate port
    >>> start_metrics_server(9090)
    >>>
    >>> # Create collector and record metrics
    >>> metrics = MetricsCollector()
    >>> metrics.record_request(
    ...     endpoint="/chat",
    ...     method="POST",
    ...     status=200,
    ...     latency=0.5,
    ...     model="gpt-4",
    ... )
    >>> metrics.record_tokens(
    ...     input_tokens=100,
    ...     output_tokens=50,
    ...     model="gpt-4",
    ...     session_id="abc123",
    ... )

Installation:
    pip install consoul[prometheus]
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy imports for optional dependency
_prometheus_available: bool | None = None
_Counter: Any = None
_Histogram: Any = None
_Gauge: Any = None


def _import_prometheus() -> bool:
    """Lazily import prometheus-client, caching the result."""
    global _prometheus_available, _Counter, _Histogram, _Gauge

    if _prometheus_available is not None:
        return _prometheus_available

    try:
        from prometheus_client import Counter, Gauge, Histogram

        _Counter = Counter
        _Histogram = Histogram
        _Gauge = Gauge
        _prometheus_available = True
        return True
    except ImportError:
        logger.warning(
            "prometheus-client not installed. Metrics disabled. "
            "Install with: pip install consoul[prometheus]"
        )
        _prometheus_available = False
        return False


class MetricsCollector:
    """Collects and exposes Prometheus metrics for Consoul server.

    Metrics collected:
    - consoul_request_total: Request count by endpoint, method, status, model
    - consoul_request_latency_seconds: Request latency histogram
    - consoul_token_usage_total: Token usage by direction, model, session
    - consoul_active_sessions: Gauge of active sessions
    - consoul_tool_executions_total: Tool execution count by name, status
    - consoul_errors_total: Error count by endpoint, error type

    Gracefully degrades to no-op if prometheus-client not installed.

    Example:
        >>> metrics = MetricsCollector()
        >>> metrics.record_request("/chat", "POST", 200, 0.5, "gpt-4")
        >>> metrics.record_tokens(100, 50, "gpt-4", "session123")
        >>> metrics.record_tool_execution("bash_execute", success=True)
    """

    def __init__(self) -> None:
        """Initialize metrics collector.

        Creates Prometheus Counter, Histogram, and Gauge objects.
        No-op if prometheus-client is not installed.
        """
        if not _import_prometheus():
            self._enabled = False
            return

        self._enabled = True

        self.request_count = _Counter(
            "consoul_request_total",
            "Total request count",
            ["endpoint", "method", "status", "model"],
        )
        self.request_latency = _Histogram(
            "consoul_request_latency_seconds",
            "Request latency in seconds",
            ["endpoint", "method"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )
        self.token_usage = _Counter(
            "consoul_token_usage_total",
            "Token usage count",
            ["direction", "model", "session_id"],
        )
        self.active_sessions = _Gauge(
            "consoul_active_sessions",
            "Number of active sessions",
        )
        self.tool_executions = _Counter(
            "consoul_tool_executions_total",
            "Tool execution count",
            ["tool_name", "status"],
        )
        self.error_count = _Counter(
            "consoul_errors_total",
            "Error count",
            ["endpoint", "error_type"],
        )

    @property
    def enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self._enabled

    def record_request(
        self,
        endpoint: str,
        method: str,
        status: int,
        latency: float,
        model: str = "unknown",
    ) -> None:
        """Record a request metric.

        Args:
            endpoint: API endpoint path (e.g., "/chat")
            method: HTTP method (e.g., "POST")
            status: HTTP status code
            latency: Request latency in seconds
            model: Model name (e.g., "gpt-4")
        """
        if not self._enabled:
            return
        self.request_count.labels(
            endpoint=endpoint,
            method=method,
            status=str(status),
            model=model,
        ).inc()
        self.request_latency.labels(endpoint=endpoint, method=method).observe(latency)

    def record_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        session_id: str = "unknown",
    ) -> None:
        """Record token usage metrics.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
            session_id: Session identifier for aggregation
        """
        if not self._enabled:
            return
        self.token_usage.labels(
            direction="input",
            model=model,
            session_id=session_id,
        ).inc(input_tokens)
        self.token_usage.labels(
            direction="output",
            model=model,
            session_id=session_id,
        ).inc(output_tokens)

    def record_tool_execution(self, tool_name: str, success: bool) -> None:
        """Record a tool execution.

        Args:
            tool_name: Name of the tool (e.g., "bash_execute")
            success: Whether the execution was successful
        """
        if not self._enabled:
            return
        status = "success" if success else "failure"
        self.tool_executions.labels(tool_name=tool_name, status=status).inc()

    def record_error(self, endpoint: str, error_type: str) -> None:
        """Record an error.

        Args:
            endpoint: API endpoint where error occurred
            error_type: Type of error (e.g., "validation", "internal", "timeout")
        """
        if not self._enabled:
            return
        self.error_count.labels(endpoint=endpoint, error_type=error_type).inc()

    def set_active_sessions(self, count: int) -> None:
        """Set the number of active sessions.

        Args:
            count: Number of active sessions
        """
        if not self._enabled:
            return
        self.active_sessions.set(count)


def start_metrics_server(port: int = 9090) -> bool:
    """Start Prometheus metrics HTTP server on separate port.

    Starts a simple HTTP server that exposes /metrics endpoint.
    Runs in a background thread.

    Args:
        port: Port to listen on (default: 9090)

    Returns:
        True if server started successfully, False otherwise.

    Example:
        >>> if start_metrics_server(9090):
        ...     print("Metrics available at http://localhost:9090/metrics")
    """
    if not _import_prometheus():
        return False

    try:
        from prometheus_client import start_http_server

        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
        return True
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(
                f"Metrics port {port} already in use (likely already started)"
            )
            return True  # Already running is OK
        logger.error(f"Failed to start metrics server: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        return False
