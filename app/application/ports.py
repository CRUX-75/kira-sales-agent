"""Ports (interfaces) implemented by the infrastructure layer."""

from datetime import datetime
from typing import Protocol

from app.domain.state_machine import Session


class SessionRepository(Protocol):
    def get(self, conversation_id: str) -> Session | None: ...

    def save(self, conversation_id: str, session: Session) -> None: ...

    def delete_older_than(self, cutoff: datetime) -> int:
        """Delete sessions last saved before `cutoff` (retention). Returns how many."""
        ...
