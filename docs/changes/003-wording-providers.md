# 003 — Wording providers and comparison

## Goal

Plug a real LLM behind the `WordingClient` port and choose the provider with measurements on
this project's own task, not with generic benchmarks.

## Scope

- `application/prompts.py`: provider-independent prompt builder. The customer message is
  fenced as data (prompt-injection hardening); validators remain the real safety net.
- `infrastructure/llm_openai.py` (Chat Completions) and `llm_anthropic.py` (Messages API):
  one HTTP attempt per call, no sampling parameters (rejected by Claude Haiku 5.5), `effort`
  configurable, token usage recorded, HTTP error bodies kept for diagnosis.
- `infrastructure/llm_factory.py` + settings: `WORDING_PROVIDER=none|openai|anthropic`.
  Default is `none` (templates only), so nothing calls a provider unless configured.
- `application/evaluation.py` + `scripts/compare_wording.py`: same scenarios for every
  candidate, validity decided by the deterministic validators, blind human review for tone.

## Decision criteria (fixed before running the comparison)

1. **Fallback rate** (all attempts invalid -> template): lower is better, target 0 %.
2. **First-try valid rate**: higher means fewer retries, lower cost and latency.
3. **Blind review** of naturalness on the same scenarios (5 to 10 minutes, key hidden).
4. **Latency p95**: target under 3 s per call.
5. **Cost per 1,000 messages**: tie-breaker only. At $0.10 / $0.50 per 1M tokens it is a few
   cents, so quality must not be traded for cost.

Rule: pick the cheapest candidate that is not worse than the best one on criteria 1 to 3.
A mid-tier model ($2 / $10) is only justified if the economical tier fails criterion 1 or 3.

## How to run

```bash
# smoke test: 3 scenarios, one candidate, costs a fraction of a cent
python scripts/compare_wording.py --limit 3 openai:gpt-6-luna:low

# full comparison (prints the table and writes docs/evals/*)
python scripts/compare_wording.py openai:gpt-6-luna:low anthropic:claude-haiku-5-5:low
```

If a call fails, the provider error appears under "Provider errors" in the report
(for example a rejected parameter). Fix the adapter, not the validators.

## Not tested against the real APIs here

Adapters are covered by tests with a mocked HTTP transport. Their first real call is the
smoke test above. Prices in `scripts/compare_wording.py` are list prices of October 2026.
