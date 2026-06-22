"""Per-thread SessionManager provider that gives the orchestrator durable memory.

ag_ui_strands invokes this once per thread_id (lock-guarded) and attaches the returned
manager to that thread's Strands ``Agent``. With a session manager present, Strands owns
conversation history: it rehydrates prior turns on ``Agent`` init and persists each new
turn — ag_ui_strands then passes only the latest user message, so history is never
double-counted.

History is stored in Postgres (see ``postgres_session_manager``), keyed by the AG-UI
thread_id as the session id. When no connection string is configured we return ``None`` and
the agent runs with in-memory history only, so a missing/misconfigured store degrades
gracefully instead of failing the turn.
"""

import asyncio
import logging
from typing import Optional

from ag_ui.core import RunAgentInput
from strands.session import SessionManager

from config import config
from postgres_session_manager import PostgresSessionManager
from request_context import get_request_context

logger = logging.getLogger(__name__)


async def get_session_manager(input_data: RunAgentInput) -> Optional[SessionManager]:
    """Build a ``PostgresSessionManager`` for this thread, or ``None`` to run without persistence."""
    db_url = config.session_db_url
    if not db_url:
        logger.warning(
            "[SESSION] SESSION_DATABASE_URL not configured; running without persistent memory"
        )
        return None

    session_id = input_data.thread_id
    if not session_id:
        logger.warning(
            "[SESSION] No thread_id on request; running without persistent memory"
        )
        return None

    # user_id is required — it owns the session row (NOT NULL) and scopes the lookup tool.
    # It always accompanies an authenticated request; if it's somehow absent we skip
    # persistence rather than write an unattributable session.
    raw_user_id = get_request_context().user_id
    try:
        user_id = int(raw_user_id) if raw_user_id is not None else None
    except (TypeError, ValueError):
        user_id = None
    if user_id is None:
        logger.warning(
            f"[SESSION] No valid user_id on request (got {raw_user_id!r}); "
            "running without persistent memory"
        )
        return None

    logger.info(f"[SESSION] Attaching Postgres memory: session_id={session_id} user_id={user_id}")

    # Building the manager opens a pooled connection and reads/creates the session row —
    # blocking I/O — so run it off the event loop.
    def _build() -> PostgresSessionManager:
        return PostgresSessionManager(session_id=session_id, conninfo=db_url, user_id=user_id)

    try:
        return await asyncio.to_thread(_build)
    except Exception as e:
        # A memory-store hiccup must never take down the turn; fall back to in-memory.
        logger.error(
            f"[SESSION] Failed to initialize PostgresSessionManager ({e}); "
            "running without persistent memory",
            exc_info=True,
        )
        return None
