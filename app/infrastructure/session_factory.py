"""Pick the session repository from settings: PostgreSQL if DATABASE_URL is set."""

from app.application.ports import SessionRepository
from app.config import Settings
from app.infrastructure.sessions_memory import InMemorySessionRepository
from app.infrastructure.sessions_postgres import PostgresSessionRepository


def build_session_repository(settings: Settings) -> SessionRepository:
    if settings.database_url:
        return PostgresSessionRepository(settings.database_url)
    return InMemorySessionRepository()  # development only: sessions are lost on restart
