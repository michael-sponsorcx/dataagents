"""Postgres-backed Strands SessionManager for durable orchestrator conversation memory.

Mirrors Strands' own ``FileSessionManager``: this class is both a ``RepositorySessionManager``
(so it plugs into the Agent's rehydrate-on-init / persist-after-turn hooks) and a
``SessionRepository`` (the storage backend). We only swap file I/O for Postgres rows.

The Strands session model is a 3-level tree — one Session contains many SessionAgents,
each of which contains an ordered list of SessionMessages — and every entity round-trips
through ``to_dict()`` / ``from_dict()``. We store each entity as a JSONB ``data`` column,
keyed by its identifiers, in three SCX-owned tables:

    ai_agent_sessions(session_id UNIQUE, data, ...)
    ai_agent_session_agents(session_id, agent_id, data, ..., UNIQUE(session_id, agent_id))
    ai_agent_session_messages(session_id, agent_id, message_id, data, ...,
                              UNIQUE(session_id, agent_id, message_id))

These tables are owned and migrated by the SCX API
(api/db/migrations/..._create_ai_agent_session_tables.sql); this agent performs NO DDL.
The functional key columns (session_id, agent_id, message_id, data) are the contract — if
the SCX migration renames them, update the queries here to match.

The interface is synchronous (Strands calls these hooks inline during the agent run), so we
use psycopg (v3) with a small connection pool. Per-call connections are short; the pool keeps
them warm.
"""

import atexit
import logging
from typing import TYPE_CHECKING, Any, Optional

from psycopg_pool import ConnectionPool
from psycopg.types.json import Jsonb

from strands.types.exceptions import SessionException
from strands.types.session import Session, SessionAgent, SessionMessage
from strands.session.repository_session_manager import RepositorySessionManager
from strands.session.session_repository import SessionRepository

if TYPE_CHECKING:
    from strands.multiagent.base import MultiAgentBase

logger = logging.getLogger(__name__)

# SCX-owned table names (created by the SCX API migration; this agent never issues DDL).
_T_SESSIONS = "ai_agent_sessions"
_T_AGENTS = "ai_agent_session_agents"
_T_MESSAGES = "ai_agent_session_messages"

# One process-wide pool, shared across all per-thread session managers. Keyed by conninfo
# so a misconfiguration can't silently fan out multiple pools.
_POOL: Optional[ConnectionPool] = None
_POOL_CONNINFO: Optional[str] = None


def _get_pool(conninfo: str) -> ConnectionPool:
    """Lazily open the shared connection pool (no schema bootstrap — SCX owns the tables)."""
    global _POOL, _POOL_CONNINFO
    if _POOL is not None:
        if _POOL_CONNINFO != conninfo:
            raise SessionException(
                "Postgres session pool already initialized with a different conninfo"
            )
        return _POOL

    # min_size=0 so we never hold connections when idle; the pool grows on demand.
    pool = ConnectionPool(conninfo=conninfo, min_size=0, max_size=5, open=True, timeout=10)
    _POOL = pool
    _POOL_CONNINFO = conninfo
    return pool


@atexit.register
def _close_pool() -> None:
    """Close the shared pool on interpreter shutdown so worker threads exit cleanly."""
    global _POOL
    if _POOL is not None:
        _POOL.close()
        _POOL = None


# --- Read helpers for the session-lookup tool -------------------------------------------
# These read the same SCX tables but don't need a per-session manager instance — the tool
# just needs the shared pool. They return plain dicts/lists ready to hand to the model.


def fetch_session_messages(
    conninfo: str, session_id: str, agent_id: str = "default", limit: int = 50
) -> list[dict[str, Any]]:
    """Return a session's messages oldest-first as ``[{role, text, message_id}, ...]``."""
    pool = _get_pool(conninfo)
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT data FROM {_T_MESSAGES} WHERE session_id = %s AND agent_id = %s "
            "ORDER BY message_id DESC LIMIT %s",
            (session_id, agent_id, limit),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for (data,) in reversed(rows):  # DESC+reverse => newest kept under limit, returned oldest-first
        sm = SessionMessage.from_dict(data)
        msg = sm.message or {}
        text = " ".join(
            part["text"] for part in msg.get("content", []) if isinstance(part, dict) and "text" in part
        )
        out.append({"message_id": sm.message_id, "role": msg.get("role"), "text": text})
    return out


def fetch_user_sessions(conninfo: str, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Return a user's sessions newest-first with a preview of the first user message."""
    pool = _get_pool(conninfo)
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT s.session_id, s.created_at, s.updated_at,
                   (SELECT m.data FROM {_T_MESSAGES} m
                     WHERE m.session_id = s.session_id AND m.agent_id = 'default'
                     ORDER BY m.message_id ASC LIMIT 1) AS first_msg
              FROM {_T_SESSIONS} s
             WHERE s.user_id = %s
             ORDER BY s.updated_at DESC
             LIMIT %s
            """,
            (user_id, limit),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for session_id, created_at, updated_at, first_msg in rows:
        preview = ""
        if first_msg:
            msg = SessionMessage.from_dict(first_msg).message or {}
            preview = " ".join(
                p["text"] for p in msg.get("content", []) if isinstance(p, dict) and "text" in p
            )[:160]
        out.append({
            "session_id": session_id,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "preview": preview,
        })
    return out


class PostgresSessionManager(RepositorySessionManager, SessionRepository):
    """Strands SessionManager that persists session/agent/message state to Postgres."""

    def __init__(self, session_id: str, conninfo: str, user_id: int, **kwargs: Any):
        """Initialize with a Postgres connection.

        Args:
            session_id: ID for the session (the AG-UI thread_id).
            conninfo: libpq connection string / URL (e.g. ``postgresql://user:pw@host/db``).
            user_id: The owning user's id, stamped onto the session row (required, NOT NULL).
            **kwargs: Forwarded for future extensibility.
        """
        self._pool = _get_pool(conninfo)
        self._user_id = user_id
        # super().__init__ may create the session row (via create_session), so set _user_id first.
        super().__init__(session_id=session_id, session_repository=self)

    # --- Session -------------------------------------------------------------

    def create_session(self, session: Session, **kwargs: Any) -> Session:
        with self._pool.connection() as conn:
            cur = conn.execute(
                f"INSERT INTO {_T_SESSIONS} (session_id, user_id, data) VALUES (%s, %s, %s) "
                "ON CONFLICT (session_id) DO NOTHING",
                (session.session_id, self._user_id, Jsonb(session.to_dict())),
            )
            if cur.rowcount == 0:
                raise SessionException(f"Session {session.session_id} already exists")
        return session

    def read_session(self, session_id: str, **kwargs: Any) -> Session | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                f"SELECT data FROM {_T_SESSIONS} WHERE session_id = %s",
                (session_id,),
            ).fetchone()
        return Session.from_dict(row[0]) if row else None

    def delete_session(self, session_id: str, **kwargs: Any) -> None:
        with self._pool.connection() as conn:
            # Agents and messages are removed by ON DELETE CASCADE on the session FK.
            cur = conn.execute(f"DELETE FROM {_T_SESSIONS} WHERE session_id = %s", (session_id,))
            if cur.rowcount == 0:
                raise SessionException(f"Session {session_id} does not exist")

    # --- Agent ---------------------------------------------------------------

    def create_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                f"INSERT INTO {_T_AGENTS} (session_id, agent_id, data) "
                "VALUES (%s, %s, %s) ON CONFLICT (session_id, agent_id) "
                "DO UPDATE SET data = EXCLUDED.data, updated_at = now()",
                (session_id, session_agent.agent_id, Jsonb(session_agent.to_dict())),
            )

    def read_agent(self, session_id: str, agent_id: str, **kwargs: Any) -> SessionAgent | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                f"SELECT data FROM {_T_AGENTS} WHERE session_id = %s AND agent_id = %s",
                (session_id, agent_id),
            ).fetchone()
        return SessionAgent.from_dict(row[0]) if row else None

    def update_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        previous = self.read_agent(session_id=session_id, agent_id=session_agent.agent_id)
        if previous is None:
            raise SessionException(f"Agent {session_agent.agent_id} in session {session_id} does not exist")
        # Preserve original creation time, like FileSessionManager.
        session_agent.created_at = previous.created_at
        with self._pool.connection() as conn:
            conn.execute(
                f"UPDATE {_T_AGENTS} SET data = %s, updated_at = now() "
                "WHERE session_id = %s AND agent_id = %s",
                (Jsonb(session_agent.to_dict()), session_id, session_agent.agent_id),
            )

    # --- Message -------------------------------------------------------------

    def create_message(self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                f"INSERT INTO {_T_MESSAGES} (session_id, agent_id, message_id, data) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (session_id, agent_id, message_id) "
                "DO UPDATE SET data = EXCLUDED.data, updated_at = now()",
                (session_id, agent_id, session_message.message_id, Jsonb(session_message.to_dict())),
            )

    def read_message(self, session_id: str, agent_id: str, message_id: int, **kwargs: Any) -> SessionMessage | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                f"SELECT data FROM {_T_MESSAGES} "
                "WHERE session_id = %s AND agent_id = %s AND message_id = %s",
                (session_id, agent_id, message_id),
            ).fetchone()
        return SessionMessage.from_dict(row[0]) if row else None

    def update_message(self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any) -> None:
        previous = self.read_message(
            session_id=session_id, agent_id=agent_id, message_id=session_message.message_id
        )
        if previous is None:
            raise SessionException(f"Message {session_message.message_id} does not exist")
        session_message.created_at = previous.created_at
        with self._pool.connection() as conn:
            conn.execute(
                f"UPDATE {_T_MESSAGES} SET data = %s, updated_at = now() "
                "WHERE session_id = %s AND agent_id = %s AND message_id = %s",
                (Jsonb(session_message.to_dict()), session_id, agent_id, session_message.message_id),
            )

    def list_messages(
        self, session_id: str, agent_id: str, limit: int | None = None, offset: int = 0, **kwargs: Any
    ) -> list[SessionMessage]:
        sql = (
            f"SELECT data FROM {_T_MESSAGES} "
            "WHERE session_id = %s AND agent_id = %s ORDER BY message_id"
        )
        params: list[Any] = [session_id, agent_id]
        if limit is not None:
            sql += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        elif offset:
            sql += " OFFSET %s"
            params.append(offset)
        with self._pool.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [SessionMessage.from_dict(r[0]) for r in rows]

    # --- Multi-agent (not used by the orchestrator, implemented for completeness) ----

    def create_multi_agent(self, session_id: str, multi_agent: "MultiAgentBase", **kwargs: Any) -> None:
        raise SessionException("Multi-agent sessions are not supported by PostgresSessionManager")

    def read_multi_agent(self, session_id: str, multi_agent_id: str, **kwargs: Any) -> dict[str, Any] | None:
        return None

    def update_multi_agent(self, session_id: str, multi_agent: "MultiAgentBase", **kwargs: Any) -> None:
        raise SessionException("Multi-agent sessions are not supported by PostgresSessionManager")
