"""In-memory session repository: tests and local development (lost on restart).

It stores serialised dicts, like the database does, so codec bugs show up in tests.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.application.session_codec import session_from_dict, session_to_dict
from app.domain.state_machine import Session


class InMemorySessionRepository:
    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._items: dict[str, tuple[dict[str, Any], datetime]] = {}

    def get(self, conversation_id: str) -> Session | None:
        item = self._items.get(conversation_id)
        return session_from_dict(item[0]) if item else None

    def save(self, conversation_id: str, session: Session) -> None:
        self._items[conversation_id] = (session_to_dict(session), self._clock())

    def delete_older_than(self, cutoff: datetime) -> int:
        stale = [key for key, (_, saved_at) in self._items.items() if saved_at < cutoff]
        for key in stale:
            del self._items[key]
        return len(stale)
