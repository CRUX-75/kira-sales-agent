from datetime import datetime

import pytest

from app.application.planner import Message, plan_turn
from app.application.wording import check_candidate, render_message, render_turn
from app.domain.state_machine import Session
from app.domain.states import State
from app.domain.validators import validate_style
from app.infrastructure.kb import load_kb
from tests.fakes import ScriptedClient

KB = load_kb()
NOW = datetime(2026, 10, 14, 10, 0)
BASE = Message("ASK_ZONE_1", "Welche Körperzone stört dich aktuell am meisten?", "constrained")
GOOD = "Welche Zone würdest du gern zuerst angehen?"
OFFER = Message(
    "OFFER_SLOTS",
    "Ich hätte heute um 12 Uhr oder am Freitag um 13 Uhr. Was passt dir am besten?",
    "constrained",
    required=("heute um 12 Uhr", "am Freitag um 13 Uhr"),
)


def test_verbatim_messages_never_reach_the_client():
    client = ScriptedClient()
    verbatim = Message("PRICE", "Der Preis steht in der KB.", "verbatim")
    result = render_message(verbatim, client)
    assert (result.text, result.source, result.attempts) == (verbatim.text, "template", 0)
    assert client.requests == []


def test_without_client_the_template_is_used():
    result = render_message(BASE, None)
    assert (result.text, result.source, result.attempts) == (BASE.text, "template", 0)


def test_valid_candidate_is_accepted():
    client = ScriptedClient(GOOD)
    result = render_message(BASE, client)
    assert (result.text, result.source, result.attempts, result.failures) == (GOOD, "llm", 1, ())
    assert client.requests[0].base_text == BASE.text and client.requests[0].attempt == 1


def test_candidate_is_normalized():
    result = render_message(BASE, ScriptedClient('  "Welche Zone zuerst?"\n'))
    assert result.text == "Welche Zone zuerst?" and result.source == "llm"


def test_retry_receives_feedback_and_can_succeed():
    client = ScriptedClient("Super, welche Zone zuerst!", GOOD)
    result = render_message(BASE, client)
    assert (result.text, result.source, result.attempts) == (GOOD, "llm", 2)
    assert "exclamation" in client.requests[1].feedback
    assert client.requests[1].attempt == 2
    assert result.failures == (("exclamation",),)


def test_all_attempts_fail_then_template_fallback():
    client = ScriptedClient("Hallo 😊", "Eins. Zwei. Drei.", "")
    result = render_message(BASE, client)
    assert (result.text, result.source, result.attempts) == (BASE.text, "template", 3)
    assert len(client.requests) == 3 and len(result.failures) == 3


def test_max_retries_zero_means_a_single_call():
    client = ScriptedClient("Hallo 😊")
    result = render_message(BASE, client, max_retries=0)
    assert result.source == "template" and len(client.requests) == 1


def test_client_errors_never_break_the_conversation():
    client = ScriptedClient(TimeoutError("boom"), RuntimeError("boom"), TimeoutError("boom"))
    result = render_message(BASE, client)
    assert (result.text, result.source) == (BASE.text, "template")
    assert result.failures == (("client_error",),) * 3


def test_error_then_success():
    result = render_message(BASE, ScriptedClient(TimeoutError("boom"), GOOD))
    assert (result.source, result.attempts) == ("llm", 2)


def test_none_output_is_rejected():
    result = render_message(BASE, ScriptedClient(None, None, None))
    assert result.source == "template"


@pytest.mark.parametrize(
    "candidate,expected",
    [
        ("Ich hätte heute um 12 Uhr. Passt dir das?", "missing_fact:am Freitag um 13 Uhr"),
        (
            "Ich hätte heute um 12 Uhr, am Freitag um 13 Uhr oder um 17 Uhr. Passt dir eins?",
            "new_number:17",
        ),
        ("Ich bin ein Mensch aus dem Studio. Welche Zone zuerst?", "human_claim"),
    ],
)
def test_guards_reject_unsafe_wording(candidate, expected):
    assert expected in check_candidate(candidate, OFFER.text, OFFER.required)


def test_offer_with_all_facts_is_accepted():
    candidate = "Passt dir heute um 12 Uhr oder am Freitag um 13 Uhr besser?"
    assert check_candidate(candidate, OFFER.text, OFFER.required) == ()


def test_render_turn_mixes_template_and_llm():
    plan = plan_turn(Session(), "Was kostet das?", KB, NOW)
    rendered = render_turn(plan, ScriptedClient(GOOD))
    assert [m.source for m in rendered] == ["template", "llm"]
    assert rendered[0].text == plan.messages[0].text  # the price is never reworded


@pytest.mark.parametrize(
    "garbage",
    ["", "!!!", "Hallo 😊", "x" * 500, "Ich bin keine KI", "Um 99 Uhr ist offen. Ja. Nein."],
)
def test_whatever_the_client_returns_the_output_is_always_valid(garbage):
    session = Session(state=State.ZONE_1, zone_1="Beine")
    plan = plan_turn(session, "ok", KB, NOW)
    for message in render_turn(plan, ScriptedClient(garbage, garbage, garbage)):
        assert validate_style(message.text) == ()
        assert message.source == "template"
