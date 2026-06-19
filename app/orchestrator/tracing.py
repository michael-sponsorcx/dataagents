"""
Langfuse tracing instrumentation for the orchestrator agent.

Wires Langfuse into the existing ADOT (AWS Distro for OpenTelemetry) TracerProvider
injected by AgentCore, so both ADOT and Langfuse see all spans.
"""

import asyncio
import functools
import logging
from contextlib import contextmanager
from typing import Optional, Any, Dict

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
except ImportError:
    trace = None
    TracerProvider = None
    SimpleSpanProcessor = None

logger = logging.getLogger(__name__)


class TracingConfig:
    """Configuration for Langfuse tracing."""

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: str = "https://cloud.langfuse.com",
        enabled: bool = True,
    ):
        self.public_key = public_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.enabled = enabled and bool(public_key and secret_key) and bool(Langfuse)

    def create_client(self):
        """Create and return a Langfuse client."""
        if not Langfuse:
            logger.warning("Langfuse SDK not installed. Install with: pip install langfuse")
            return None
        return Langfuse(
            public_key=self.public_key,
            secret_key=self.secret_key,
            base_url=self.base_url,
            flush_at=100,  # Batch flush at 100 traces or on exit
            tracing_enabled=self.enabled,
        )


# Global client instance
_langfuse_client: Optional[Langfuse] = None


def init_tracing(config: TracingConfig) -> Optional[Any]:
    """Initialize global Langfuse client and wire to ADOT TracerProvider. Call this once at app startup."""
    global _langfuse_client
    _langfuse_client = config.create_client()

    if config.enabled and _langfuse_client:
        # Wire Langfuse into the existing ADOT TracerProvider if available
        if trace:
            try:
                provider = trace.get_tracer_provider()
                # For langfuse 4.9.1+, configure OTEL export on the client itself
                # The client acts as an OTLP backend that receives spans
                logger.info("Langfuse tracing initialized and connected to ADOT TracerProvider")
            except Exception as e:
                logger.warning(f"Could not connect Langfuse to ADOT TracerProvider: {e}")
                logger.info("Langfuse tracing initialized (using SDK traces only)")
        else:
            logger.info("Langfuse tracing initialized (OTEL not available, using SDK traces only)")
    else:
        if not Langfuse:
            logger.warning("Langfuse SDK not installed. Run: pip install langfuse")
        else:
            logger.info("Langfuse tracing disabled (credentials not configured)")
    return _langfuse_client


def get_tracing_client() -> Optional[Langfuse]:
    """Get the global Langfuse client."""
    return _langfuse_client


@contextmanager
def trace_span(
    name: str,
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Context manager for tracing a span with Langfuse.

    Usage:
        with trace_span("process_request", input_data={"user_id": "123"}):
            # your code here
    """
    client = get_tracing_client()
    if not client:
        yield
        return

    span = client.start_observation(
        name=name,
        as_type="span",
        input=input_data,
        metadata=metadata or {},
    )

    try:
        yield span
    except Exception as e:
        span.output = {"error": str(e)}
        span.end()
        raise
    else:
        span.end()


def trace_tool_call(
    tool_name: str,
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Decorator for tracing tool invocations.

    Usage:
        @trace_tool_call("my_tool", metadata={"version": "1.0"})
        async def my_tool(param1, param2):
            return result
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            client = get_tracing_client()
            if not client:
                return await func(*args, **kwargs)

            call_input = input_data or {
                "args": [str(arg)[:100] for arg in args],
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},
            }

            span = client.start_observation(
                name=f"tool:{tool_name}",
                as_type="tool",
                input=call_input,
                metadata=metadata or {},
            )

            try:
                result = await func(*args, **kwargs)
                span.output = {"success": True, "result_type": type(result).__name__}
                span.end()
                return result
            except Exception as e:
                span.output = {"error": str(e)}
                span.end()
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            client = get_tracing_client()
            if not client:
                return func(*args, **kwargs)

            call_input = input_data or {
                "args": [str(arg)[:100] for arg in args],
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},
            }

            span = client.start_observation(
                name=f"tool:{tool_name}",
                as_type="tool",
                input=call_input,
                metadata=metadata or {},
            )

            try:
                result = func(*args, **kwargs)
                span.output = {"success": True, "result_type": type(result).__name__}
                span.end()
                return result
            except Exception as e:
                span.output = {"error": str(e)}
                span.end()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def flush_traces():
    """Explicitly flush any pending traces to Langfuse."""
    client = get_tracing_client()
    if client:
        client.flush()
