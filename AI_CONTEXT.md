# AI_CONTEXT.md — Kira Sales Agent (reference implementation)

## Purpose

This file is the **current operational context** for AI-assisted development on this repository.
It answers, quickly:

- what this project is and what it is not;
- which architectural rules are non-negotiable;
- what the conversation flow, states and topics are (single source of truth);
- what is in scope now and what is roadmap;
- what the next useful step is.

It is **not a changelog**. History lives in Git and `docs/`.

---

## What this project is

Kira is a **rule-governed conversational sales agent** for WhatsApp, built in Python as a
reference implementation of the same architecture used in the Elvira / Respirarte project.

- It is a **portfolio use case**, not a production system and not a client deliverable.
- The business is **fictional**: *Studio Aurea*, a body-contouring studio.
  All knowledge-base content is written from scratch for this repository.
- Goal of the conversation: qualify a lead, capture two body zones, agree a time window,
  offer up to three slots and register a booking request.

Core principle:

```
WhatsApp transports.
FastAPI receives.
PostgreSQL persists.
The state machine decides.
The KB informs.
The LLM only writes wording.
Validators enforce style.
Tests protect.
```

The LLM never decides: state, intent, next action, facts (price, hours, address), opt-out,
escalation, or booking confirmation.

---

## Transparency (design decision, non-negotiable)

Kira **always identifies itself as an AI assistant**.

- The first message states that Kira is the digital assistant of the studio.
- Asked "are you a bot / human / AI?", Kira answers honestly and deterministically
  (topic `AI_DISCLOSURE`, priority 0, verbatim answer).
- No invented personal life, no pretending to "ask a colleague", no artificial waiting times
  to simulate a human. A typing indicator and a short minimum delay (<= 2 s) are allowed.
- A human at the studio confirms every booking.

Reason: honest design, and the EU AI Act (Art. 50) transparency duty for chatbots.

---

## Pipeline

```
WhatsApp Cloud API
→ FastAPI webhook
→ payload parser
→ message-id deduplication
→ load session (PostgreSQL)
→ input sanitization
→ KB Gate (deterministic topics, priority table)
→ zone detection (whitelist + aliases)
→ state machine (transition table)
→ response plan (facts + slots + next question)
→ wording: verbatim template OR LLM constrained wording
→ style validator (retry x2, then template fallback)
→ persist interaction + state
→ send reply
```

---

## States and transitions

States: `ST_INIT`, `ST_ZONE_1`, `ST_ZONE_2`, `ST_SLOT_OFFER`, `ST_BOOKED`,
`ST_CLOSED`, `ST_OPTOUT`, `ST_HANDOFF`.

`ST_ZONE_2` means: both zones captured, time-window question (morning / afternoon) pending.

| From | Trigger | To |
|---|---|---|
| any | opt-out intent | `ST_OPTOUT` (wins from any state) |
| any | medical question / human requested | `ST_HANDOFF` |
| `ST_INIT` | valid zone | `ST_ZONE_1` |
| `ST_ZONE_1` | second valid zone (different from first) | `ST_ZONE_2` |
| `ST_INIT` | two valid zones in one message | `ST_ZONE_2` |
| `ST_ZONE_2` | time-window preference given | `ST_SLOT_OFFER` (max 3 slots) |
| `ST_SLOT_OFFER` | explicit slot choice | `ST_BOOKED` (booking *request*) |
| `ST_INIT`..`ST_SLOT_OFFER` | explicit rejection or 3 objections | `ST_CLOSED` |

Rules: states are never inferred from free text by the LLM. A topic answer (price, hours...)
never changes the state. After a topic answer the flow resumes at the pending question.

---

## KB topics (priority: lower number wins)

| Topic | Priority | Wording | Notes |
|---|---|---|---|
| `AI_DISCLOSURE` | 0 | verbatim | honest answer, offers human contact |
| `OPTOUT` | 0 | verbatim | persists, excludes future outbound |
| `PRICE` | 1 | verbatim | fixed offer text from KB, no discounts |
| `ZONES` | 2 | constrained | closed list: Bauch, Beine, Po, Arme, Rücken |
| `ADDRESS` | 3 | verbatim | fictional address |
| `HOURS` | 4 | verbatim | per-day table, single source in KB |
| `TRANSIT` | 5 | verbatim | |
| `BOOKING` | 6 | constrained | max 3 slots, weekday + time, no year |
| `OBJECTION` | 7 | constrained | max 3 attempts, then `ST_CLOSED` |
| `GREETING` | 8 | verbatim | includes the AI disclosure |
| `OTHER` | 99 | constrained | short answer + redirect to the flow |

Collision rule: only the highest-priority topic is answered; the other is kept for follow-up.

---

## Style rules (enforced by validator, not by prompt)

- German, informal "du", warm and short.
- Max 2 sentences and max 160 characters.
- No emojis, no exclamation marks.
- No medical promises or diagnoses; results claims are not allowed.
- If wording fails validation twice, use the deterministic template.

---

## Scope

**In scope (MVP):** webhook, deduplication, state machine, KB gate, constrained wording,
validators, PostgreSQL persistence, safe test endpoint (no real sending), pytest suite.

**Roadmap (documented, not built):** Instagram / Facebook, voice notes (STT/TTS),
image input, contextual follow-ups, A/B testing, real calendar integration.

---

## Repository structure

```
kira-sales-agent/
├── app/ (api, domain, application, infrastructure)
├── data/kb/            # fictional KB, single source of truth
├── docs/
├── scripts/
├── tests/
├── AI_CONTEXT.md
├── Dockerfile
├── .env.example
└── requirements.txt
```

Important: no `src/` folder; this repository uses `app/`.

---

## Repository rules

- No material from any third-party client: no names, scripts, KB text, numbers or briefs.
- Never commit `.env`; only `.env.example`.
- Every behaviour change needs an explicit test.
- Report only real, reproducible numbers (e.g. the output of `pytest -q`).
- Describe the project as a reference implementation, not as a production deployment.

---

## Current status

Done: skeleton, fictional KB, `domain/` (states, zones, signals, state machine with chained
advance, KB gate, slot generator, style validator) and `application/planner.py`
(session + user text -> new session + messages), all covered by pytest.

The planner is pure: each `Message` has a deterministic `text` that is always valid, a
`wording` mode (`verbatim` | `constrained`) and `required` facts (slots) that any LLM
rewording must preserve (`validators.missing_facts`).

## Next step

1. LLM wording port: reword `constrained` messages, validate (`validate_style` +
   `missing_facts`), retry x2, then fall back to `Message.text`.
2. Session persistence (PostgreSQL) and persistence of `deferred` topics.
3. WhatsApp webhook: parser, message-id deduplication, safe test endpoint (no real sending).
4. Conversation log and metrics (fallback rate, handoff rate, bookings requested).
