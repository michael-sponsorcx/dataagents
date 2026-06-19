"""
FastAPI middleware for Langfuse tracing integration.

Automatically traces incoming requests and attaches user/session context.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
from tracing import get_tracing_client

logger = logging.getLogger(__name__)


class LangfuseTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that traces incoming requests to Langfuse.

    Captures:
    - Request path and method
    - Response status code
    - Execution time
    - Optional user_id and session_id from headers or query params
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client = get_tracing_client()
        if not client:
            return await call_next(request)

        user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id")
        session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
        request_id = request.headers.get("X-Request-ID")

        span_name = f"{request.method} {request.url.path}"
        span_input = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
        }

        metadata = {"feature": "api_request"}
        if user_id:
            metadata["user_id"] = user_id
        if session_id:
            metadata["session_id"] = session_id
        if request_id:
            metadata["request_id"] = request_id

        span = client.start_observation(
            name=span_name,
            as_type="span",
            input=span_input,
            metadata=metadata,
        )

        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            span.output = {
                "status_code": response.status_code,
                "duration_ms": int(duration * 1000),
            }
            span.end()
            return response
        except Exception as e:
            duration = time.time() - start_time
            span.output = {
                "error": str(e),
                "duration_ms": int(duration * 1000),
            }
            span.end()
            raise
