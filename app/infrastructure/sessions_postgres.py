"""PostgreSQL session repository (psycopg 3, plain SQL).

One short-lived connection per call: simple and safe at WhatsApp volumes. A connection pool
is a later optimisation. Writes are last-write-wins; the webhook will serialise messages
per conversation (see docs/changes/005-session-persistence.md).
"""

from datetime import datetime

import psycopg
from psycopg.types.json import Jsonb

from app.application.session_codec import session_from_dict, session_to_dict
from app.domain.state_machine import Session


class PostgresSessionRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def get(self, conversation_id: str) -> Session | None:
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                "SELECT data FROM conversation_sessions WHERE conversation_id = %s",
                (conversation_id,),
            ).fetchone()
        return session_from_dict(row[0]) if row else None

    def save(self, conversation_id: str, session: Session) -> None:
        with psycopg.connect(self._dsn) as conn:
            conn.execute(
                """
                INSERT INTO conversation_sessions (conversation_id, data)
                VALUES (%s, %s)
                ON CONFLICT (conversation_id)
                DO UPDATE SET data = EXCLUDED.data, updated_at = now()
                """,
                (conversation_id, Jsonb(session_to_dict(session))),
            )

    def delete_older_than(self, cutoff: datetime) -> int:
        with psycopg.connect(self._dsn) as conn:
            cursor = conn.execute(
                "DELETE FROM conversation_sessions WHERE updated_at < %s", (cutoff,)
            )
            return cursor.rowcount
