# 002 — LLM wording port

## Goal

Let an LLM reword the messages marked `constrained` so conversations sound varied and human,
without ever trusting it: every candidate is validated by deterministic code and the template
is always the fallback.

## Scope

**Part 1 (this change) — provider-independent port**

- `WordingClient` Protocol, `WordingRequest`, `RenderedMessage`.
- `render_message` / `render_turn`: first attempt + 2 retries (max 3 calls), feedback with the
  violations of the previous attempt, template fallback, provider errors never propagate.
- Guards on every candidate: style (`validate_style`), required facts (`missing_facts`),
  no invented numbers (`introduced_numbers`), no human claims (`human_claims`).
- Tests use a scripted fake client. No network, no API key.

**Part 2 (next) — provider adapter**

- Prompt builder (system + user prompt from `WordingRequest`), unit-tested.
- Provider adapter behind `WordingClient`, with timeout and one HTTP attempt per call.
- Settings: provider, model, timeout. Real provider call stays out of the test suite.

## Acceptance criteria

- [x] Verbatim messages never reach the client.
- [x] An invalid candidate is retried with feedback; after the last failure the template is used.
- [x] A client exception counts as a failed attempt and never breaks the turn.
- [x] Whatever the client returns, the final text passes `validate_style`.
- [x] Slots and other required facts survive; no new numbers; no human claims.
- [x] `ruff check`, `ruff format --check` and `pytest` (coverage >= 90 %) pass.

## Decisions

- Synchronous port for now; an async adapter can wrap it when the webhook needs it.
- "retry x2" means first attempt plus two retries.
