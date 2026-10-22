# 005 — Session persistence

## Goal

Keep each conversation's state between WhatsApp messages, behind a port, so the planner and
the webhook never depend on a database.

## Scope

- `application/ports.py`: `SessionRepository` Protocol (`get`, `save`, `delete_older_than`).
- `application/session_codec.py`: `Session` <-> JSON-safe dict, versioned (`v`).
- `application/retention.py`: `purge_expired_sessions(repo, ttl_days)`.
- `infrastructure/sessions_memory.py`: in-memory repository for tests and local development.
- `infrastructure/sessions_postgres.py`: PostgreSQL adapter, psycopg 3, plain SQL, upsert.
- `infrastructure/migrations.py` + `migrations/001_*.sql` + `scripts/migrate.py`.
- `infrastructure/session_factory.py`: PostgreSQL if `DATABASE_URL` is set, memory otherwise.

## Schema

```sql
conversation_sessions (
    conversation_id TEXT PRIMARY KEY,
    data            JSONB NOT NULL,        -- session_to_dict(), versioned
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

## Decisions

- **psycopg directly, no ORM:** one table, three queries; full control and fewer dependencies.
- **One short-lived connection per call:** simple and enough at WhatsApp volumes. A pool is a
  later optimisation.
- **Stored sessions are versioned:** an unknown version raises `ValueError` instead of being
  guessed. The webhook decides what to do (it must never crash a conversation).
- **Migrations run in one transaction:** all pending ones apply or none.

## Privacy and retention

- A session holds zones, time preference, offered slots and counters. No name, phone number or
  free text.
- `conversation_id` must be an HMAC-SHA256 of the WhatsApp number with a secret key, never the
  raw number. It is generated in the webhook task.
- Sessions older than `SESSION_TTL_DAYS` (default 7) are deleted by `purge_expired_sessions`,
  which will run on a schedule.

## Known limitation

Writes are last-write-wins. Two messages of the same conversation processed at the same time
could overwrite each other. The webhook task serialises processing per conversation
(`pg_advisory_xact_lock`) and deduplicates by `message_id`.

## Running the PostgreSQL tests

Without a database the PostgreSQL tests are skipped (the memory variant always runs). With
Docker:

```bash
docker run --name kira-pg -e POSTGRES_USER=kira -e POSTGRES_PASSWORD=kira_test \
  -e POSTGRES_DB=kira_test -p 5432:5432 -d postgres:16
export TEST_DATABASE_URL=postgresql://kira:kira_test@localhost:5432/kira_test
pytest -q
```

## Acceptance criteria

- [x] The same contract tests pass for the memory and the PostgreSQL repository.
- [x] Upsert keeps a single row; every save refreshes `updated_at`.
- [x] Retention deletes only expired sessions.
- [x] Migrations are idempotent, ordered and atomic.
- [x] `ruff`, `ruff format --check` and `pytest` (coverage >= 90 %) pass, with and without a
      database.
