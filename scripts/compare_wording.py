"""Compare LLM wording providers on identical scenarios (validity, cost, latency).

Usage, from the repository root, with keys in .env or in the environment:

    python scripts/compare_wording.py --limit 3 openai:gpt-6-luna:low   # cheap smoke test
    python scripts/compare_wording.py openai:gpt-6-luna:low anthropic:claude-haiku-5-5:low

Each spec is provider:model:effort. The report goes to docs/evals/. A blind review file
(outputs shuffled and labelled A/B/...) lets a human judge naturalness without knowing which
model wrote what; the key is stored separately.
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.application.evaluation import (  # noqa: E402
    CandidateResult,
    build_scenarios,
    percentile,
    run_candidate,
)
from app.config import get_settings  # noqa: E402
from app.infrastructure.kb import load_kb  # noqa: E402
from app.infrastructure.llm_anthropic import AnthropicWordingClient  # noqa: E402
from app.infrastructure.llm_openai import OpenAIWordingClient  # noqa: E402

# USD per 1M tokens (input, output), standard tier, prompts below the long-context threshold.
# Checked in October 2026. Verify on the provider pricing pages before trusting the cost column.
PRICES = {
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6.1-sol": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}


def build_client(spec: str):
    provider, model, *rest = spec.split(":")
    effort = rest[0] if rest else "low"
    settings = get_settings()
    timeout = settings.wording_timeout_seconds
    if provider == "openai":
        if not settings.openai_api_key:
            sys.exit("OPENAI_API_KEY is not set")
        return OpenAIWordingClient(settings.openai_api_key, model, effort=effort, timeout=timeout)
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            sys.exit("ANTHROPIC_API_KEY is not set")
        return AnthropicWordingClient(
            settings.anthropic_api_key, model, effort=effort, timeout=timeout
        )
    sys.exit(f"Unknown provider in spec {spec!r} (use openai or anthropic)")


def format_table(results: list[CandidateResult]) -> str:
    header = (
        "| Candidate | Messages | First-try valid | LLM used | Unchanged | Fallback "
        "| Avg attempts | p50 s | p95 s | Tokens in/out | USD per 1,000 messages |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for r in results:
        model = r.name.split(":")[1]
        cost = f"{r.cost_per_1000_messages(PRICES[model]):.4f}" if model in PRICES else "n/a"
        rows.append(
            f"| {r.name} | {r.messages} | {r.first_try_rate:.0%} | {r.llm_rate:.0%} "
            f"| {r.unchanged_rate:.0%} | {r.fallback_rate:.0%} | {r.mean_attempts:.2f} "
            f"| {percentile(r.latencies, 0.5):.2f} | {percentile(r.latencies, 0.95):.2f} "
            f"| {r.input_tokens}/{r.output_tokens} | {cost} |"
        )
    return header + "\n".join(rows)


def format_details(results: list[CandidateResult]) -> str:
    lines = []
    for r in results:
        lines.append(f"### {r.name}")
        lines.append(f"- Violations: {dict(r.violations) or 'none'}")
        lines.append(f"- Provider errors: {dict(r.errors) or 'none'}")
    return "\n".join(lines)


def write_blind_review(results, scenarios, out_dir: Path, stamp: str, seed: int) -> None:
    rng = random.Random(seed)
    key: dict[str, dict[str, str]] = {}
    lines = [
        "# Blind review",
        "",
        "For each scenario pick the most natural, friendly and clear message (A, B, ...).",
        "Ignore length differences you cannot justify. Do not open the key file before you finish.",
        "",
    ]
    for scenario in scenarios:
        order = list(results)
        rng.shuffle(order)
        labels = {chr(65 + i): r for i, r in enumerate(order)}
        key[scenario.id] = {label: r.name for label, r in labels.items()}
        lines += [
            f"## {scenario.id}",
            f"Customer: {scenario.user_text}",
            f"Template (baseline): {scenario.message.text}",
            "",
        ]
        lines += [f"- **{label}**: {r.outputs[scenario.id]}" for label, r in labels.items()]
        lines.append("")
    (out_dir / f"{stamp}-blind-review.md").write_text("\n".join(lines), encoding="utf-8")
    (out_dir / f"{stamp}-blind-key.json").write_text(
        json.dumps(key, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("specs", nargs="+", help="provider:model:effort")
    parser.add_argument("--limit", type=int, default=0, help="only the first N scenarios")
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="docs/evals")
    args = parser.parse_args()

    scenarios = build_scenarios(load_kb(), datetime.now())
    if args.limit:
        scenarios = scenarios[: args.limit]
    results = [
        run_candidate(spec, build_client(spec), scenarios, max_retries=args.max_retries)
        for spec in args.specs
    ]

    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = (
        f"# Wording comparison {stamp}\n\n"
        f"{len(scenarios)} identical scenarios, max {args.max_retries} retries, "
        f"validators decide validity.\n\n{format_table(results)}\n\n{format_details(results)}\n"
    )
    (out_dir / f"{stamp}-wording-comparison.md").write_text(report, encoding="utf-8")
    if len(results) > 1:
        write_blind_review(results, scenarios, out_dir, stamp, args.seed)
    print(report)
    print(f"Files written to {out_dir}/")


if __name__ == "__main__":
    main()
