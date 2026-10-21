# Wording comparison 2026-10-21-0752

28 identical scenarios, max 2 retries, validators decide validity.

| Candidate | Messages | First-try valid | LLM used | Unchanged | Fallback | Avg attempts | p50 s | p95 s | Tokens in/out | USD per 1,000 messages |
|---|---|---|---|---|---|---|---|---|---|---|
| openai:gpt-6-luna:none | 28 | 100% | 100% | 18% | 0% | 1.00 | 1.33 | 2.05 | 8779/699 | 0.0438 |
| anthropic:claude-haiku-5-5:low | 28 | 100% | 100% | 36% | 0% | 1.00 | 0.90 | 1.53 | 13622/1337 | 0.0725 |

### openai:gpt-6-luna:none
- Violations: none
- Provider errors: none
### anthropic:claude-haiku-5-5:low
- Violations: none
- Provider errors: none
