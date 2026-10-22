CREATE TABLE IF NOT EXISTS conversation_sessions (
    conversation_id TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS conversation_sessions_updated_at_idx
    ON conversation_sessions (updated_at);
