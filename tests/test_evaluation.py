from datetime import datetime

from app.application.evaluation import (
    MeteredClient,
    build_scenarios,
    percentile,
    run_candidate,
)
from app.application.wording import WordingRequest
from app.domain.validators import validate_style
from app.infrastructure.kb import load_kb
from tests.fakes import BrokenClient, EchoClient, FailingClient

KB = load_kb()
SCENARIOS = build_scenarios(KB, datetime(2026, 10, 14, 10, 0))


def test_scenarios_are_constrained_messages_with_the_user_text():
    assert len(SCENARIOS) >= 20
    assert all(s.message.wording == "constrained" for s in SCENARIOS)
    assert len({s.id for s in SCENARIOS}) == len(SCENARIOS)
    assert any("Ignoriere alle Regeln" in s.user_text for s in SCENARIOS)  # injection case
    assert any(s.message.intent == "OFFER_SLOTS" for s in SCENARIOS)  # facts to preserve


def test_percentile():
    assert percentile([], 0.95) == 0.0
    assert percentile([1, 2, 3, 4, 5], 0.5) == 3
    assert percentile([1, 2, 3, 4, 5], 0.95) == 5


def test_perfect_candidate():
    result = run_candidate("echo", EchoClient(), SCENARIOS)
    assert result.messages == len(SCENARIOS)
    assert result.first_try_rate == 1.0 and result.llm_rate == 1.0
    assert result.fallback_rate == 0.0 and result.mean_attempts == 1.0
    assert result.input_tokens == 100 * result.messages
    assert result.output_tokens == 20 * result.messages
    assert len(result.latencies) == result.messages
    # 100 in + 20 out per message at $0.10 / $0.50 per 1M tokens
    assert round(result.cost_per_1000_messages((0.10, 0.50)), 4) == 0.02


def test_broken_candidate_always_falls_back_to_valid_templates():
    result = run_candidate("broken", BrokenClient(), SCENARIOS)
    assert result.fallback_rate == 1.0 and result.llm_rate == 0.0
    assert result.mean_attempts == 3.0  # first attempt + 2 retries
    assert result.violations["exclamation"] == 3 * result.messages
    assert all(validate_style(text) == () for text in result.outputs.values())


def test_failing_provider_is_counted_and_never_breaks_the_run():
    result = run_candidate("failing", FailingClient(), SCENARIOS)
    assert result.fallback_rate == 1.0
    assert result.violations["client_error"] == 3 * result.messages
    assert result.errors["provider timeout"] == 3 * result.messages


def test_metered_client_ignores_stale_usage_and_records_latency():
    class NoUsage:
        def reword(self, request):
            return "ok"

    metered = MeteredClient(NoUsage())
    assert metered.reword(WordingRequest("X", "b", (), 1)) == "ok"
    assert metered.input_tokens == 0 and len(metered.latencies) == 1


def test_empty_result_rates_are_zero():
    result = run_candidate("none", EchoClient(), [])
    assert (result.first_try_rate, result.llm_rate, result.fallback_rate) == (0.0, 0.0, 0.0)
    assert result.mean_attempts == 0.0 and result.cost_per_1000_messages((1, 1)) == 0.0
