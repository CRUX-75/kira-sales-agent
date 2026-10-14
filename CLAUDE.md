# CLAUDE.md — working rules for AI-assisted development

Read `AI_CONTEXT.md` first: it is the single source of truth for architecture, states,
topics and style rules. If this file and `AI_CONTEXT.md` disagree, `AI_CONTEXT.md` wins.

## How to work

1. **Small tasks, one at a time.** One task = one branch (`feat/...`, `fix/...`, `chore/...`)
   and one reviewable change. Never skip ahead.
2. **Tests first or together with the code.** Every behaviour change needs an explicit test.
3. **Quality gates before every commit:**
   ```bash
   ruff check . && ruff format --check . && pytest -q
   ```
   `pytest` enforces coverage >= 90 % (see `pytest.ini`).
4. **Conventional commits:** `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
5. **English only** for code, comments, docs and commit messages. User-facing German text
   lives in `data/kb/studio_aurea.json`, never inline in code.
6. **Fully typed Python 3.12**, clean layers: `domain` (pure) -> `application` -> `infrastructure`.
   The domain layer never does I/O and never calls an LLM.

## Non-negotiable rules

- The LLM only rewords messages marked `constrained`; it never decides state, intent, facts
  or booking. Output must pass `validate_style` and `missing_facts`, else use `Message.text`.
- Kira always identifies itself as an AI assistant.
- No third-party client material in this repository. The business is fictional.
- Never commit `.env` or secrets. Only `.env.example`.
- Report only real, reproducible numbers (output of `pytest -q`), never estimates.
- Describe the project as a reference implementation, not as a production deployment.
