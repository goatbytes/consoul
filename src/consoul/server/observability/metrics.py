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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response

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
    - consoul_redis_degraded: Gauge for Redis degradation status (SOUL-328)
    - consoul_redis_recovered_total: Counter for Redis recovery events (SOUL-328)
    - consoul_circuit_breaker_state: Circuit breaker state by provider (SOUL-342)
    - consoul_circuit_breaker_trips_total: Circuit breaker trip count (SOUL-342)
    - consoul_circuit_breaker_rejections_total: Requests rejected by breaker (SOUL-342)

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

        # Redis degradation metrics (SOUL-328)
        self.redis_degraded = _Gauge(
            "consoul_redis_degraded",
            "Whether Redis is in degraded mode (1=degraded, 0=healthy)",
        )
        self.redis_recovered = _Counter(
            "consoul_redis_recovered_total",
            "Total number of Redis connection recoveries",
        )

        # Circuit breaker metrics (SOUL-342)
        self.circuit_breaker_state = _Gauge(
            "consoul_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=half-open, 2=open)",
            ["provider"],
        )
        self.circuit_breaker_trips_total = _Counter(
            "consoul_circuit_breaker_trips_total",
            "Total number of times circuit breaker has tripped",
            ["provider"],
        )
        self.circuit_breaker_rejections_total = _Counter(
            "consoul_circuit_breaker_rejections_total",
            "Total requests rejected by open circuit breaker",
            ["provider"],
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

    def set_redis_degraded(self, value: int) -> None:
        """Set Redis degraded gauge (SOUL-328).

        Args:
            value: 1 if degraded, 0 if healthy
        """
        if not self._enabled:
            return
        self.redis_degraded.set(value)

    def increment_redis_recovered(self) -> None:
        """Increment Redis recovery counter (SOUL-328)."""
        if not self._enabled:
            return
        self.redis_recovered.inc()

    def set_circuit_breaker_state(self, provider: str, state: int) -> None:
        """Set circuit breaker state (SOUL-342).

        Args:
            provider: LLM provider name (e.g., "openai", "anthropic")
            state: Circuit state (0=closed, 1=half-open, 2=open)
        """
        if not self._enabled:
            return
        self.circuit_breaker_state.labels(provider=provider).set(state)

    def record_circuit_breaker_trip(self, provider: str) -> None:
        """Record circuit breaker trip (SOUL-342).

        Args:
            provider: LLM provider name (e.g., "openai", "anthropic")
        """
        if not self._enabled:
            return
        self.circuit_breaker_trips_total.labels(provider=provider).inc()

    def record_circuit_breaker_rejection(self, provider: str) -> None:
        """Record request rejected by circuit breaker (SOUL-342).

        Args:
            provider: LLM provider name (e.g., "openai", "anthropic")
        """
        if not self._enabled:
            return
        self.circuit_breaker_rejections_total.labels(provider=provider).inc()


def create_metrics_middleware(
    metrics: MetricsCollector | None,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Create Starlette middleware that records request metrics.

    Records request count, latency, and error counts for all HTTP requests.
    Metrics are recorded ONLY if a MetricsCollector is provided and enabled.

    Args:
        metrics: MetricsCollector instance or None

    Returns:
        Starlette middleware callable that records metrics.

    Example:
        >>> from fastapi import FastAPI
        >>> from starlette.middleware.base import BaseHTTPMiddleware
        >>> app = FastAPI()
        >>> metrics = MetricsCollector()
        >>> app.add_middleware(BaseHTTPMiddleware, dispatch=create_metrics_middleware(metrics))
    """
    import time

    from starlette.requests import Request as StarletteRequest  # noqa: TC002
    from starlette.responses import Response as StarletteResponse  # noqa: TC002

    async def metrics_middleware(
        request: StarletteRequest,
        call_next: Callable[[StarletteRequest], Awaitable[StarletteResponse]],
    ) -> StarletteResponse:
        """Record request metrics (latency, status, endpoint)."""
        if metrics is None or not metrics.enabled:
            return await call_next(request)

        start_time = time.perf_counter()
        status = 500  # Default to 500 if exception occurs
        response: StarletteResponse | None = None

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            # Record metrics for unhandled exceptions before re-raising
            latency = time.perf_counter() - start_time
            endpoint = request.url.path
            method = request.method

            metrics.record_request(
                endpoint=endpoint,
                method=method,
                status=500,
                latency=latency,
                model="unknown",
            )
            metrics.record_error(endpoint=endpoint, error_type="unhandled_exception")
            raise
        else:
            # Record metrics for successful responses (including error responses)
            latency = time.perf_counter() - start_time
            endpoint = request.url.path
            method = request.method

            metrics.record_request(
                endpoint=endpoint,
                method=method,
                status=status,
                latency=latency,
                model="unknown",  # Model recorded separately in chat endpoint
            )

            # Record errors for 4xx/5xx responses
            if status >= 400:
                error_type = "client_error" if status < 500 else "server_error"
                metrics.record_error(endpoint=endpoint, error_type=error_type)

        return response

    return metrics_middleware


def create_app_state_metrics_middleware() -> Callable[
    [Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]
]:
    """Create middleware that looks up metrics from app.state at request time.

    Unlike create_metrics_middleware which captures metrics at creation time,
    this version looks up request.app.state.metrics on each request. This allows
    the middleware to be added before app startup while metrics are initialized
    during the lifespan handler.

    Returns:
        Starlette middleware callable that records metrics.

    Example:
        >>> from fastapi import FastAPI
        >>> from starlette.middleware.base import BaseHTTPMiddleware
        >>> app = FastAPI()
        >>> app.state.metrics = None  # Will be set in lifespan
        >>> app.add_middleware(
        ...     BaseHTTPMiddleware,
        ...     dispatch=create_app_state_metrics_middleware()
        ... )
    """
    import time

    from starlette.requests import Request as StarletteRequest  # noqa: TC002
    from starlette.responses import Response as StarletteResponse  # noqa: TC002

    async def metrics_middleware(
        request: StarletteRequest,
        call_next: Callable[[StarletteRequest], Awaitable[StarletteResponse]],
    ) -> StarletteResponse:
        """Record request metrics (latency, status, endpoint)."""
        # Look up metrics from app.state at request time
        metrics: MetricsCollector | None = getattr(request.app.state, "metrics", None)

        if metrics is None or not metrics.enabled:
            return await call_next(request)

        start_time = time.perf_counter()
        status = 500  # Default to 500 if exception occurs
        response: StarletteResponse | None = None

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            # Record metrics for unhandled exceptions before re-raising
            latency = time.perf_counter() - start_time
            endpoint = request.url.path
            method = request.method

            metrics.record_request(
                endpoint=endpoint,
                method=method,
                status=500,
                latency=latency,
                model="unknown",
            )
            metrics.record_error(endpoint=endpoint, error_type="unhandled_exception")
            raise
        else:
            # Record metrics for successful responses (including error responses)
            latency = time.perf_counter() - start_time
            endpoint = request.url.path
            method = request.method

            metrics.record_request(
                endpoint=endpoint,
                method=method,
                status=status,
                latency=latency,
                model="unknown",  # Model recorded separately in chat endpoint
            )

            # Record errors for 4xx/5xx responses
            if status >= 400:
                error_type = "client_error" if status < 500 else "server_error"
                metrics.record_error(endpoint=endpoint, error_type=error_type)

        return response

    return metrics_middleware


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
            # Port bound by another process - metrics won't be recorded here
            # This is a deployment error, not a success condition
            logger.error(
                f"Metrics port {port} already in use by another process. "
                "Metrics will NOT be recorded. Use a different port or ensure "
                "only one worker binds the metrics port."
            )
            return False
        logger.error(f"Failed to start metrics server: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        return False
