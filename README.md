# Kira Sales Agent

[![CI](https://github.com/CRUX-75/kira-sales-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/CRUX-75/kira-sales-agent/actions/workflows/ci.yml)

A rule-governed WhatsApp sales conversation agent, built in Python as a **reference
implementation** of a deterministic conversational architecture (state machine + knowledge
base + constrained LLM wording + validators).

> Portfolio use case. Fictional business (*Studio Aurea*), not a production system.
> Kira always identifies itself as an AI assistant.

```
WhatsApp transports. FastAPI receives. PostgreSQL persists.
The state machine decides. The KB informs. The LLM only writes wording.
Validators enforce style. Tests protect.
```

## Status

Domain core and turn planner: states, zone detection, signals, state machine, KB gate,
slot generator, style validator, response planner and a fictional KB. LLM wording,
persistence and the WhatsApp webhook are the next steps.
See `AI_CONTEXT.md` for the architecture and the roadmap.

## Channels

The core is channel-agnostic. The first real channel is **Telegram** (test channel, no
review process); the WhatsApp Cloud API is planned as a later adapter. Plan:
`docs/changes/007-telegram-channel-and-deployment.md`.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest -q   # enforces coverage >= 90 %; PostgreSQL tests need TEST_DATABASE_URL (see docs/changes/005)
python scripts/chat_cli.py        # talk to Kira in the terminal
uvicorn app.main:app --reload
curl http://127.0.0.1:8000/health
```
