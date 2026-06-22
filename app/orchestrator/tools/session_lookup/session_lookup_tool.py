"""Tool: let the orchestrator look up conversation history without writing SQL.

This *complements* the automatic SessionManager (which silently rehydrates the current
turn's context). The model calls this only when it explicitly needs to look further back —
e.g. to recall something earlier in a long thread, or to reference one of the user's prior
conversations. All SQL lives in ``postgres_session_manager``; the model just picks a scope.

Identity is resolved from the per-request context the middleware set, so the model never
supplies (and cannot spoof) the user_id or session_id.
"""

import json
import logging
import sys
from pathlib import Path

from strands import tool

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import config
from request_context import get_request_context
from postgres_session_manager import fetch_session_messages, fetch_user_sessions

logger = logging.getLogger(__name__)

TOOL_DESCRIPTION = (
    "Look up this user's prior conversation history with you. "
    "Use scope='current' to re-read earlier messages in the CURRENT conversation (e.g. to "
    "recall a detail from many turns ago), or scope='past_sessions' to list the user's "
    "EARLIER conversations (with a short preview of each) so you can reference them. "
    "You do not need to provide user or session ids — they are taken from the request."
)


@tool(description=TOOL_DESCRIPTION)
async def look_up_session_history(scope: str = "current", limit: int = 50) -> str:
    """Return conversation history for the current user.

    Args:
        scope: 'current' for messages in the active conversation (oldest-first), or
            'past_sessions' to list the user's earlier conversations (newest-first).
        limit: Max rows to return (messages or sessions depending on scope).

    Returns:
        JSON string: {"status", "scope", and "messages" or "sessions"} or an error.
    """
    db_url = config.session_db_url
    if not db_url:
        return json.dumps({"status": "unavailable", "reason": "session store not configured"})

    ctx = get_request_context()
    try:
        if scope == "past_sessions":
            if not ctx.user_id:
                return json.dumps({"status": "unavailable", "reason": "no user in request context"})
            sessions = fetch_user_sessions(db_url, ctx.user_id, limit=min(limit, 50))
            return json.dumps({"status": "success", "scope": scope, "sessions": sessions})

        # default: current session
        if not ctx.session_id:
            return json.dumps({"status": "unavailable", "reason": "no session in request context"})
        messages = fetch_session_messages(db_url, ctx.session_id, limit=min(limit, 200))
        return json.dumps({"status": "success", "scope": "current", "messages": messages})
    except Exception as e:
        logger.error(f"[SESSION] look_up_session_history failed: {e}", exc_info=True)
        return json.dumps({"status": "error", "error": str(e)})
