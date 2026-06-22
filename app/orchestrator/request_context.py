"""Per-request identity propagated from the FastAPI middleware to the agent and tools.

The orchestrator builds the Strands ``Agent`` per thread (via ag_ui_strands), and the
``ask_ai_analyst`` tool needs the caller's identity that the model never sees. Rather than
thread request args through ag_ui_strands, we stash them in a ``ContextVar`` set in the
middleware before ``call_next``.

This is safe because Starlette's ``BaseHTTPMiddleware`` runs the downstream app in an
anyio child task, and contextvars are *copied into* that child task at spawn time — so a
value set here before ``call_next`` is visible inside the agent and its tools. Propagation
is one-directional (down only): values set inside a tool are NOT visible back in the
middleware, which is fine since we only ever read these downstream.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RequestContext:
    """Identity for the current request. ``session_id`` is the AG-UI thread_id."""

    session_id: Optional[str] = None
    user_id: Optional[str] = None
    authorized_email: Optional[str] = None


_request_context: ContextVar[RequestContext] = ContextVar(
    "orchestrator_request_context", default=RequestContext()
)


def set_request_context(
    *,
    session_id: Optional[str],
    user_id: Optional[str],
    authorized_email: Optional[str],
) -> None:
    """Set the current request's identity. Call once per request in the middleware."""
    _request_context.set(
        RequestContext(
            session_id=session_id,
            user_id=user_id,
            authorized_email=authorized_email,
        )
    )


def get_request_context() -> RequestContext:
    """Read the current request's identity (empty ``RequestContext`` outside a request)."""
    return _request_context.get()
