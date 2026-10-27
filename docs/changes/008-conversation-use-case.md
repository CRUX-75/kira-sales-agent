# 008 — Conversation use case

Step A of `007-telegram-channel-and-deployment.md`.

## Goal

One entry point that joins session repository, planner and wording client, independent of any
channel: `ConversationService.handle(conversation_id, text) -> ConversationResult`.

## Scope

- `application/conversation.py`: the service, input normalisation (whitespace, 1000 characters
  maximum) and `berlin_now()`.
- `infrastructure/service_factory.py`: the composition root (settings -> service).
- `scripts/chat_cli.py`: talk to Kira in the terminal, no channel and no server needed.
- `tzdata` added to the requirements: slim container images ship no timezone database.

## Decisions

- **Time zone:** slots are computed with Berlin local time (`berlin_now`). A container runs in
  UTC, and a plain `datetime.now()` would offer slots one or two hours off.
- **Unreadable stored session:** a new conversation starts and `session_reset=True` is
  returned so the caller can log it. A broken record never blocks a customer.
- **Provider errors:** already contained by the wording port; the template is sent.
- **Not in this step:** per-conversation locking and message deduplication. They need the
  database and belong to the channel adapter (step B).

## Acceptance criteria

- [x] State survives between messages and after a restart (new service, same storage).
- [x] Conversations are isolated; opt-out is stored.
- [x] Only `constrained` messages reach the wording client; a failing client changes nothing
      for the customer.
- [x] Unreadable sessions start over and are flagged; empty and oversized input are safe.
- [x] The composition root works with the default settings (no provider, memory storage).
- [x] `ruff`, `pytest` (coverage >= 90 %) and CI stay green.
