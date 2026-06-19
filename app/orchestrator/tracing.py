"""
Langfuse tracing instrumentation for the orchestrator agent.

Exports spans directly to Langfuse via OTLP, bypassing AgentCore's ADOT.
All observability flows to Langfuse exclusively.
"""

import logging
from typing import Optional, Any

try:
    from langfuse import Langfuse, propagate_attributes
except ImportError:
    Langfuse = None
    propagate_attributes = None

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.processors.baggage.baggage_span_processor import BaggageSpanProcessor
except ImportError:
    trace = None
    TracerProvider = None
    SimpleSpanProcessor = None
    BatchSpanProcessor = None
    BaggageSpanProcessor = None

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
    """Initialize global Langfuse client. Spans export via OTLP directly to Langfuse."""
    global _langfuse_client
    _langfuse_client = config.create_client()

    # Add BaggageSpanProcessor to propagate attributes from propagate_attributes() to all spans
    if BaggageSpanProcessor and trace:
        try:
            provider = trace.get_tracer_provider()
            if isinstance(provider, TracerProvider):
                # Check if BaggageSpanProcessor is already added
                existing_baggage = any(isinstance(p, BaggageSpanProcessor) for p in provider.active_span_processor_list)
                if not existing_baggage:
                    provider.add_span_processor(BaggageSpanProcessor())
                    logger.info("BaggageSpanProcessor added to OTEL tracer provider")
        except Exception as e:
            logger.warning(f"Could not add BaggageSpanProcessor: {e}")

    if config.enabled and _langfuse_client:
        logger.info("Langfuse tracing initialized (OTEL exports directly to Langfuse)")
    else:
        if not Langfuse:
            logger.warning("Langfuse SDK not installed. Run: pip install langfuse")
        else:
            logger.info("Langfuse tracing disabled (credentials not configured)")
    return _langfuse_client


def get_tracing_client() -> Optional[Langfuse]:
    """Get the global Langfuse client."""
    return _langfuse_client



def flush_traces():
    """Explicitly flush any pending traces to Langfuse."""
    client = get_tracing_client()
    if client:
        client.flush()
