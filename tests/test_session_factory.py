from app.config import Settings
from app.infrastructure.session_factory import build_session_repository
from app.infrastructure.sessions_memory import InMemorySessionRepository
from app.infrastructure.sessions_postgres import PostgresSessionRepository


def test_without_database_url_the_memory_repository_is_used():
    assert isinstance(
        build_session_repository(Settings(database_url=None)), InMemorySessionRepository
    )


def test_with_database_url_postgres_is_used_without_connecting_yet():
    repo = build_session_repository(Settings(database_url="postgresql://u:p@localhost:1/db"))
    assert isinstance(repo, PostgresSessionRepository)
