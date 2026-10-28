# 009 — Telegram channel logic

Step B1 of `007-telegram-channel-and-deployment.md`: everything about the channel that needs
no network. The HTTP layer (B2) is a thin wrapper around these functions.

## Scope

`app/channels/telegram.py` (pure functions):

- `parse_update`: private human text messages only. Edits, member changes, callbacks, group
  chats and messages from bots are ignored (no loops, no LLM cost). Content without text is
  marked `unsupported`.
- `decide`: the access policy. Allowlist of chat ids; **an empty list means nobody**.
  `/id` works for anyone and shows only their own id (to be added to the list), `/start` is
  a greeting, `/stop` an opt-out. Strangers and unsupported content get a fixed reply that
  never reaches the LLM.
- `verify_secret`: constant-time check of `X-Telegram-Bot-Api-Secret-Token`; no secret
  configured means reject.
- `conversation_id`: `tg_` + HMAC-SHA256 of the chat id with a secret key. The chat id is
  never stored; the key is required.
- `parse_allowed_chat_ids`: comma separated list, a typo fails loudly at startup.

Texts for the channel (`CHANNEL_*`) live in the KB, not in code.

## Configuration

`TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_ALLOWED_CHAT_IDS`,
`CONVERSATION_ID_SECRET`, `CHANNEL_SENDING_ENABLED` (default `false`). The old
`WHATSAPP_SENDING_ENABLED` flag became channel-neutral.

## Next (B2)

Webhook route, deduplication by `update_id` (migration 002), per-conversation lock, sender
(`sendMessage`, typing indicator) and `scripts/set_telegram_webhook.py`.

## Acceptance criteria

- [x] Only private human text reaches the conversation; groups and bots are ignored.
- [x] Fail closed: empty allowlist, missing webhook secret or missing id key reject.
- [x] A stranger can learn their own chat id and nothing else.
- [x] `/start` and `/stop` map to the greeting and the opt-out (tested through the service).
- [x] `ruff`, `pytest` (coverage >= 90 %) and CI stay green.
