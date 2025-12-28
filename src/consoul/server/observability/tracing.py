"""LangSmith and OpenTelemetry tracing integration for Consoul server.

Provides setup functions for distributed tracing integrations:
- LangSmith: LLM-focused tracing with LangChain ecosystem integration
- OpenTelemetry: Vendor-neutral distributed tracing standard

Both integrations are optional and gracefully degrade if packages not installed.

Example:
    >>> from consoul.server.observability.tracing import setup_langsmith, setup_opentelemetry
    >>>
    >>> # Setup LangSmith (requires LANGSMITH_API_KEY env var)
    >>> tracer = setup_langsmith()
    >>> if tracer:
    ...     # Use tracer as LangChain callback
    ...     model.invoke("Hello", config={"callbacks": [tracer]})
    >>>
    >>> # Setup OpenTelemetry
    >>> if setup_opentelemetry(service_name="consoul", endpoint="http://localhost:4317"):
    ...     # Traces will be exported to the collector
    ...     pass

Installation:
    pip install consoul[langsmith]  # LangSmith only
    pip install consoul[otel]       # OpenTelemetry only
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def setup_langsmith() -> Any | None:
    """Setup LangSmith tracing if configured.

    Requires LANGSMITH_API_KEY environment variable to be set.
    Returns a LangChainTracer callback that can be passed to LangChain models.

    Returns:
        LangChainTracer callback or None if not available/configured.

    Example:
        >>> import os
        >>> os.environ["LANGSMITH_API_KEY"] = "ls_..."
        >>> tracer = setup_langsmith()
        >>> if tracer:
        ...     # Use with LangChain
        ...     response = model.invoke("Hello", config={"callbacks": [tracer]})
    """
    api_key = os.environ.get("LANGSMITH_API_KEY")
    if not api_key:
        logger.debug("LANGSMITH_API_KEY not set, skipping LangSmith setup")
        return None

    try:
        from langchain_core.tracers import LangChainTracer
        from langsmith import Client

        client = Client()
        tracer = LangChainTracer(client=client)
        logger.info("LangSmith tracing enabled")
        return tracer
    except ImportError:
        logger.warning(
            "langsmith not installed. LangSmith tracing disabled. "
            "Install with: pip install consoul[langsmith]"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to setup LangSmith: {e}")
        return None


def setup_opentelemetry(
    service_name: str = "consoul",
    endpoint: str | None = None,
) -> bool:
    """Setup OpenTelemetry tracing.

    Configures the global tracer provider with OTLP exporter.
    Traces will be exported to the specified collector endpoint.

    Args:
        service_name: Service name for traces (default: "consoul")
        endpoint: OTLP collector endpoint (e.g., "http://localhost:4317").
                  Falls back to OTEL_EXPORTER_OTLP_ENDPOINT env var.

    Returns:
        True if setup successful, False otherwise.

    Example:
        >>> if setup_opentelemetry(service_name="my-service", endpoint="http://jaeger:4317"):
        ...     print("OpenTelemetry tracing enabled")
        >>>
        >>> # Or use environment variable:
        >>> import os
        >>> os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"
        >>> setup_opentelemetry()
    """
    endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.debug(
            "OTEL_EXPORTER_OTLP_ENDPOINT not set, skipping OpenTelemetry setup"
        )
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(endpoint=endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        logger.info(f"OpenTelemetry tracing enabled (endpoint: {endpoint})")
        return True
    except ImportError:
        logger.warning(
            "opentelemetry packages not installed. OpenTelemetry tracing disabled. "
            "Install with: pip install consoul[otel]"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry: {e}")
        return False


def get_tracer(name: str = "consoul") -> Any | None:
    """Get an OpenTelemetry tracer for manual instrumentation.

    Returns None if OpenTelemetry is not set up.

    Args:
        name: Tracer name (default: "consoul")

    Returns:
        OpenTelemetry Tracer or None if not available.

    Example:
        >>> tracer = get_tracer("consoul.chat")
        >>> if tracer:
        ...     with tracer.start_as_current_span("process_message") as span:
        ...         span.set_attribute("session_id", "abc123")
        ...         # Process message...
    """
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        # Check if it's the default no-op provider
        if provider.__class__.__name__ == "ProxyTracerProvider":
            return None
        return trace.get_tracer(name)
    except ImportError:
        return None
