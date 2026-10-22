"""Contract tests: every SessionRepository implementation must behave the same.

The PostgreSQL variant runs only when TEST_DATABASE_URL is set, for example:
    docker run --name kira-pg -e POSTGRES_USER=kira -e POSTGRES_PASSWORD=kira_test \
        -e POSTGRES_DB=kira_test -p 5432:5432 -d postgres:16
    export TEST_DATABASE_URL=postgresql://kira:kira_test@localhost:5432/kira_test
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest

from app.application.retention import purge_expired_sessions
from app.domain.slots import Slot
from app.domain.state_machine import Session
from app.domain.states import State
from app.infrastructure.migrations import apply_migrations
from app.infrastructure.sessions_memory import InMemorySessionRepository
from app.infrastructure.sessions_postgres import PostgresSessionRepository

DSN = os.environ.get("TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not DSN, reason="TEST_DATABASE_URL is not set")

SESSION = Session(
    state=State.SLOT_OFFER,
    zone_1="Beine",
    zone_2="Po",
    time_preference="nachmittags",
    offered_slots=(Slot(datetime(2026, 10, 14).date(), 13, "heute um 13 Uhr"),),
)


def test_in_ci_the_database_tests_are_never_skipped():
    if os.environ.get("CI"):
        assert DSN, "TEST_DATABASE_URL must be set in CI, otherwise PostgreSQL tests are skipped"


@pytest.fixture
def clean_database():
    apply_migrations(DSN)
    with psycopg.connect(DSN) as conn:
        conn.execute("TRUNCATE conversation_sessions")


@pytest.fixture(params=["memory", pytest.param("postgres", marks=needs_db)])
def repo(request):
    if request.param == "memory":
        return InMemorySessionRepository()
    request.getfixturevalue("clean_database")
    return PostgresSessionRepository(DSN)


def test_unknown_conversation_returns_none(repo):
    assert repo.get("nobody") is None


def test_save_and_get_round_trip(repo):
    repo.save("c1", SESSION)
    loaded = repo.get("c1")
    assert loaded == SESSION and loaded is not SESSION


def test_save_overwrites_the_previous_session(repo):
    repo.save("c1", SESSION)
    newer = Session(state=State.BOOKED, zone_1="Beine", zone_2="Po", chosen_slot=1)
    repo.save("c1", newer)
    assert repo.get("c1") == newer


def test_conversations_are_isolated(repo):
    repo.save("c1", SESSION)
    repo.save("c2", Session(state=State.ZONE_1, zone_1="Bauch"))
    assert repo.get("c1") == SESSION
    assert repo.get("c2").zone_1 == "Bauch"


def test_delete_older_than_with_a_fake_clock():
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    clock = iter([now - timedelta(days=10), now - timedelta(days=1)])
    repo = InMemorySessionRepository(clock=lambda: next(clock))
    repo.save("old", SESSION)
    repo.save("recent", SESSION)
    assert purge_expired_sessions(repo, ttl_days=7, now=now) == 1
    assert repo.get("old") is None and repo.get("recent") == SESSION


@needs_db
def test_postgres_upsert_keeps_a_single_row(clean_database):
    repo = PostgresSessionRepository(DSN)
    for _ in range(3):
        repo.save("c1", SESSION)
    with psycopg.connect(DSN) as conn:
        assert conn.execute("SELECT count(*) FROM conversation_sessions").fetchone()[0] == 1


@needs_db
def test_postgres_retention_deletes_only_expired_rows(clean_database):
    repo = PostgresSessionRepository(DSN)
    repo.save("old", SESSION)
    repo.save("recent", SESSION)
    with psycopg.connect(DSN) as conn:
        conn.execute(
            "UPDATE conversation_sessions SET updated_at = now() - interval '10 days' "
            "WHERE conversation_id = 'old'"
        )
    assert purge_expired_sessions(repo, ttl_days=7) == 1
    assert repo.get("old") is None and repo.get("recent") == SESSION


@needs_db
def test_postgres_updates_the_timestamp_on_every_save(clean_database):
    repo = PostgresSessionRepository(DSN)
    repo.save("c1", SESSION)
    with psycopg.connect(DSN) as conn:
        conn.execute("UPDATE conversation_sessions SET updated_at = now() - interval '10 days'")
    repo.save("c1", SESSION)  # a new message makes the session fresh again
    assert purge_expired_sessions(repo, ttl_days=7) == 0


@needs_db
def test_migrations_are_idempotent_and_ordered(clean_database, tmp_path: Path):
    assert apply_migrations(DSN) == []  # the fixture already applied the real ones
    (tmp_path / "002_b.sql").write_text("CREATE TABLE IF NOT EXISTS t_b (id int);")
    (tmp_path / "001_a.sql").write_text("CREATE TABLE IF NOT EXISTS t_a (id int);")
    try:
        assert apply_migrations(DSN, tmp_path) == ["001_a.sql", "002_b.sql"]
        assert apply_migrations(DSN, tmp_path) == []
    finally:
        with psycopg.connect(DSN) as conn:
            conn.execute("DROP TABLE IF EXISTS t_a, t_b")
            conn.execute("DELETE FROM schema_migrations WHERE name IN ('001_a.sql','002_b.sql')")


@needs_db
def test_a_failing_migration_applies_nothing(clean_database, tmp_path: Path):
    (tmp_path / "001_ok.sql").write_text("CREATE TABLE t_ok (id int);")
    (tmp_path / "002_bad.sql").write_text("THIS IS NOT SQL;")
    with pytest.raises(psycopg.Error):
        apply_migrations(DSN, tmp_path)
    with psycopg.connect(DSN) as conn:
        exists = conn.execute("SELECT to_regclass('t_ok')").fetchone()[0]
    assert exists is None
