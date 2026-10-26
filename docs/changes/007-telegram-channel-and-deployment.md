# 007 — Telegram test channel and deployment (Easypanel on Hetzner)

## Decision

- **Test channel: Telegram.** The WhatsApp Cloud API needs Meta business verification, app review
  and approved templates. Telegram gives a real phone channel in minutes, with no review.
- The architecture stays channel-agnostic: a channel adapter turns an update into
  `(conversation, text)`, the conversation use case returns messages, the adapter sends them.
  WhatsApp becomes one more adapter later; nothing in `domain/` or the planner changes.
- **Deployment:** the same pattern as the Elvira project: a Hetzner server managed with
  Easypanel, one PostgreSQL service and one app service built from this repository.

## Scope, in order (each item is its own small PR)

**A. Conversation use case** (`application/conversation.py`)
`handle_message(conversation_id, text)` loads the session, plans the turn, renders it with the
configured wording client, saves the session and returns the messages. An unreadable stored
session starts a new conversation and is logged. Tested with the memory repository and a
scripted client.

**B. Telegram adapter**
- Parser for updates: private chats only, text only; other content gets one fixed reply.
- Webhook secret check (`X-Telegram-Bot-Api-Secret-Token`), compared in constant time.
- Allowlist of chat ids during the test phase (limits who can use the bot and the LLM cost).
- `/start` is treated as a greeting; `/stop` as an opt-out.
- Deduplication by `update_id` (migration 002) and a per-conversation lock
  (`pg_advisory_xact_lock`), which closes the last-write-wins limitation of 005.
- Sender (`sendMessage`, `sendChatAction` typing), route `POST /webhook/telegram` and
  `scripts/set_telegram_webhook.py`.
- Sending is **off by default** (`CHANNEL_SENDING_ENABLED=false`).
- Conversation id = HMAC-SHA256(secret, `telegram:<chat_id>`); the chat id is never stored.

**C. Deployment hardening**
Dockerfile: non-root user, copy `migrations/` and `scripts/`, health check, run migrations
before starting the server. `docs/deploy-easypanel.md` with the step-by-step guide.

**D. Observability**
Structured logs without message text or identifiers; counters for fallback rate, handoffs and
bookings requested, so the provider decision in 004 can be revisited with real data.

## New configuration

`TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_ALLOWED_CHAT_IDS`,
`CONVERSATION_ID_SECRET`, `CHANNEL_SENDING_ENABLED`. Real values only in the Easypanel
environment, never in the repository.

## Easypanel layout

1. Project `kira` with a PostgreSQL 16 service (persistent volume).
2. App service from the GitHub repository (branch `main`, Dockerfile build, port 8000,
   health check `/health`), environment variables from the list above plus the LLM settings
   of 004, domain with automatic HTTPS.
3. First deployments are manual. Auto-deploy is enabled once CI is required on `main`.
4. After the first deployment: register the webhook, check `/ready`, send "Hallo" from a phone.

## Privacy

No message text and no identifiers in logs; sessions hold no personal data and expire after
7 days; only allowlisted chats can talk to the bot during tests; Kira introduces itself as a
digital assistant in the first message.

## Acceptance criteria

- [ ] A message from a phone gets a reply with p95 under 5 s.
- [ ] State survives between messages and after a restart.
- [ ] A duplicated update is processed once; concurrent messages of one chat are serialised.
- [ ] Sending is off by default and nothing secret is in the repository.
- [ ] `ruff`, `pytest` (coverage >= 90 %) and CI stay green.
