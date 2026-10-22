# 004 — Wording provider decision

Status: decided on 2026-10-21. Reversible by changing three lines in `.env`.

## Decision

Default provider for LLM wording: **OpenAI `gpt-6-luna` with `reasoning_effort=none`**.
Validated alternative: **Anthropic `claude-haiku-5-5` with `effort=low`**.

```bash
# default
WORDING_PROVIDER=openai
WORDING_MODEL=gpt-6-luna
WORDING_EFFORT=none

# alternative
WORDING_PROVIDER=anthropic
WORDING_MODEL=claude-haiku-5-5
WORDING_EFFORT=low
```

`WORDING_PROVIDER=none` (templates only) stays the repository default; nothing calls a
provider until it is configured.

## Rule (fixed before running, see 003)

Pick the cheapest candidate that is not worse than the best one on fallback rate, first-try
validity and blind-review tone. Latency p95 must stay under 3 s.

## Evidence

28 identical scenarios per run, validators decide validity, list prices of October 2026
(Luna $0.10 / $0.50, Haiku 5.5 $0.10 / $0.50 per 1M tokens).

| Run | Candidate | First-try valid | Unchanged | Fallback | p95 s | USD / 1,000 msgs |
|---|---|---|---|---|---|---|
| 1 | luna:none | 100 % | n/a | 0 % | 1.43 | 0.0415 |
| 1 | luna:low | 100 % | n/a | 0 % | 2.35 | 0.0599 |
| 1 | haiku:low | 96 % | n/a | 0 % | 1.09 | 0.0731 |
| 2 | luna:none | 100 % | 4 % | 0 % | 1.44 | 0.0415 |
| 2 | luna:low | 100 % | 7 % | 0 % | 2.14 | 0.0635 |
| 2 | haiku:low | 100 % | 0 % | 0 % | 1.03 | 0.0701 |
| 3 (zone guard, stricter prompt) | luna:none | 100 % | 18 % | 0 % | 2.05 | 0.0438 |
| 3 (zone guard, stricter prompt) | haiku:low | 100 % | 36 % | 0 % | 1.53 | 0.0725 |

Blind review of run 2 (one reviewer, 27 valid scenarios, ties split): haiku 11.5, luna:none
10.5, luna:low 5.0. One scenario was discarded because the winning text changed the zones;
that case led to the zone guard (`new_zone`) and to zones becoming required facts.

## Reading

- `luna:low` loses everywhere: slower, costlier, lower in the blind review.
- `luna:none` and `haiku:low` are technically tied on validity and tone. The difference of
  one point in the blind review is not distinguishable from chance.
- Haiku is about 0.5 s faster at p95 and about 65 % costlier. Both differences are irrelevant
  for an asynchronous WhatsApp reply (cents per 10,000 messages), so the pre-registered
  tie-break (cost) applies.
- With the stricter prompt and the zone guard both models copy the template more often
  (Luna 18 %, Haiku 36 %). More variety is a prompt task, not a provider task.

## Limits of this evidence

Small sample, one run per configuration, one reviewer, blind review done before the stricter
prompt, latency measured from Berlin, nondeterministic models. No real conversations yet.

## Revisit when

- fallback rate in real logs is above 2 %,
- p95 latency is above 3 s,
- the tone is criticised in real conversations,
- a new model generation or a price change is published.

Re-run `python scripts/compare_wording.py <specs>` and add the table here.
