# Wording comparison 2026-10-20-1054

28 identical scenarios, max 2 retries, validators decide validity.

| Candidate | Messages | First-try valid | LLM used | Unchanged | Fallback | Avg attempts | p50 s | p95 s | Tokens in/out | USD per 1,000 messages |
|---|---|---|---|---|---|---|---|---|---|---|
| openai:gpt-6-luna:none | 28 | 100% | 100% | 4% | 0% | 1.00 | 1.02 | 1.44 | 8061/713 | 0.0415 |
| openai:gpt-6-luna:low | 28 | 100% | 100% | 7% | 0% | 1.00 | 1.43 | 2.14 | 8061/1946 | 0.0635 |
| anthropic:claude-haiku-5-5:low | 28 | 100% | 100% | 0% | 0% | 1.00 | 0.82 | 1.03 | 12627/1402 | 0.0701 |

### openai:gpt-6-luna:none
- Violations: none
- Provider errors: none
### openai:gpt-6-luna:low
- Violations: none
- Provider errors: none
### anthropic:claude-haiku-5-5:low
- Violations: none
- Provider errors: none
