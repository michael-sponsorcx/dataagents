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
from tracing import get_tracing_client, flush_traces

try:
    from langfuse import propagate_attributes
except ImportError:
    propagate_attributes = None

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

        user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id")
        authorized_email = request.headers.get("X-Authorized-Email") or request.query_params.get("authorized_email")
        session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
        request_id = request.headers.get("X-Request-ID")

        # Extract thread_id and user context from JSON body if available (Strands agent requests)
        thread_id = None
        if request.method == "POST" and request.url.path == "/invocations":
            try:
                # body() caches the result, so it's safe to call multiple times
                body_bytes = await request.body()
                if body_bytes:
                    import json
                    body = json.loads(body_bytes)
                    thread_id = body.get("threadId")  # camelCase from Strands
                    print(f"[SESSION] threadId from body: {thread_id}", flush=True)
                    if thread_id and not session_id:
                        session_id = thread_id
                        print(f"[SESSION] Using as session_id: {session_id}", flush=True)

                    # Extract user context from context field (SCX backend sends user_id and authorized_email separately)
                    context = body.get("context", {})
                    if not user_id and "userId" in context:
                        user_id = context.get("userId")
                    if not authorized_email and "authorizedEmail" in context:
                        authorized_email = context.get("authorizedEmail")

                    # Also check for snake_case versions in top-level body
                    if not user_id and "user_id" in body:
                        user_id = body.get("user_id")
                    if not authorized_email and "authorized_email" in body:
                        authorized_email = body.get("authorized_email")
            except Exception as e:
                logger.debug(f"Could not extract context from body: {e}")

        span_name = f"{request.method} {request.url.path}"
        span_input = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
        }

        metadata = {"feature": "api_request"}
        if user_id:
            metadata["user_id"] = user_id
        if authorized_email:
            metadata["authorized_email"] = authorized_email
        if session_id:
            metadata["session_id"] = session_id
        if request_id:
            metadata["request_id"] = request_id

        # Wrap in propagate_attributes to apply user_id and session_id to all nested spans
        ctx_manager = None
        if propagate_attributes:
            ctx_kwargs = {}
            if user_id:
                ctx_kwargs["user_id"] = user_id
            if session_id:
                ctx_kwargs["session_id"] = session_id
            if ctx_kwargs:
                logger.info(f"[SESSION] Setting propagate_attributes: {ctx_kwargs}")
                ctx_manager = propagate_attributes(**ctx_kwargs)
            else:
                logger.debug(f"[SESSION] No user_id or session_id to propagate")

        try:
            if ctx_manager:
                logger.info(f"[SESSION] Using context manager for propagate_attributes")
                with ctx_manager:
                    return await call_next(request)
            else:
                logger.debug(f"[SESSION] No context manager, calling next without propagate_attributes")
                return await call_next(request)
        finally:
            flush_traces()
