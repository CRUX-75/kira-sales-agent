"""Data minimisation: sessions older than the TTL are deleted."""

from datetime import UTC, datetime, timedelta

from app.application.ports import SessionRepository


def purge_expired_sessions(
    repository: SessionRepository, ttl_days: int, now: datetime | None = None
) -> int:
    cutoff = (now or datetime.now(UTC)) - timedelta(days=ttl_days)
    return repository.delete_older_than(cutoff)
