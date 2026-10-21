# Wording comparison 2026-10-20-1041

28 identical scenarios, max 2 retries, validators decide validity.

| Candidate | Messages | First-try valid | LLM used | Fallback | Avg attempts | p50 s | p95 s | Tokens in/out | USD per 1,000 messages |
|---|---|---|---|---|---|---|---|---|---|
| openai:gpt-6-luna:none | 28 | 100% | 100% | 0% | 1.00 | 1.13 | 1.43 | 8061/712 | 0.0415 |
| openai:gpt-6-luna:low | 28 | 100% | 100% | 0% | 1.00 | 1.23 | 2.35 | 8061/1740 | 0.0599 |
| anthropic:claude-haiku-5-5:low | 28 | 96% | 100% | 0% | 1.04 | 0.80 | 1.09 | 13177/1458 | 0.0731 |

### openai:gpt-6-luna:none
- Violations: none
- Provider errors: none
### openai:gpt-6-luna:low
- Violations: none
- Provider errors: none
### anthropic:claude-haiku-5-5:low
- Violations: {'missing_fact': 1}
- Provider errors: none
