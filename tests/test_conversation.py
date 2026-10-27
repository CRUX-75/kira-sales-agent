from datetime import UTC, datetime

import pytest

from app.application.conversation import (
    MAX_INPUT_CHARS,
    ConversationService,
    berlin_now,
    normalize_input,
)
from app.config import Settings
from app.domain.states import State
from app.infrastructure.kb import load_kb
from app.infrastructure.service_factory import build_conversation_service
from app.infrastructure.sessions_memory import InMemorySessionRepository
from tests.fakes import EchoClient, FailingClient, ScriptedClient

KB = load_kb()
NOW = datetime(2026, 10, 14, 10, 0)


def make(repo=None, wording=None):
    repo = repo if repo is not None else InMemorySessionRepository()
    return ConversationService(repo, KB, wording, clock=lambda: NOW), repo


def texts(result):
    return [m.text for m in result.messages]


def test_first_message_is_the_greeting_and_the_session_is_saved():
    service, repo = make()
    result = service.handle("c1", "Hallo")
    assert "digitale Assistentin" in texts(result)[0]
    assert repo.get("c1").state is State.INIT


def test_state_survives_between_messages_and_a_restart():
    service, repo = make()
    service.handle("c1", "Beine")
    assert repo.get("c1").state is State.ZONE_1
    restarted, _ = make(repo)  # a new service on the same storage, like a redeploy
    result = restarted.handle("c1", "Po")
    assert result.session.state is State.ZONE_2
    assert "Beine und Po" in texts(result)[0]


def test_conversations_are_isolated():
    service, repo = make()
    service.handle("a", "Beine")
    service.handle("b", "Bauch")
    assert repo.get("a").zone_1 == "Beine" and repo.get("b").zone_1 == "Bauch"


def test_full_booking_flow():
    service, repo = make()
    for text in ("Hallo", "Beine", "Po", "nachmittags", "die zweite"):
        result = service.handle("c1", text)
    assert result.session.state is State.BOOKED
    chosen = result.session.offered_slots[1].label
    assert chosen in texts(result)[0]


def test_the_injected_clock_drives_the_slots():
    service, _ = make()
    for text in ("Beine und Po", "nachmittags"):
        result = service.handle("c1", text)
    assert texts(result)[0].count("heute um") == 1  # NOW is a Wednesday at 10:00


def test_without_a_wording_client_templates_are_used():
    service, _ = make(wording=None)
    result = service.handle("c1", "Beine")
    assert {m.source for m in result.messages} == {"template"}


def test_with_a_wording_client_only_constrained_messages_use_it():
    service, _ = make(wording=EchoClient())
    result = service.handle("c1", "Was kostet das?")
    assert [(m.intent, m.source) for m in result.messages] == [
        ("PRICE", "template"),
        ("ASK_ZONE_1", "llm"),
    ]


def test_a_failing_provider_never_breaks_the_conversation():
    service, repo = make(wording=FailingClient())
    result = service.handle("c1", "Beine")
    assert result.messages[0].source == "template"
    assert repo.get("c1").state is State.ZONE_1


def test_the_normalised_text_reaches_the_wording_client():
    client = ScriptedClient("Welche Zone zuerst?")
    service, _ = make(wording=client)
    service.handle("c1", "  was   kostet\n das? ")
    assert client.requests[0].user_text == "was kostet das?"


def test_long_input_is_truncated_and_empty_input_does_not_crash():
    assert len(normalize_input("a" * 5000)) == MAX_INPUT_CHARS
    service, _ = make()
    result = service.handle("c1", "   ")
    assert result.messages[0].intent == "OTHER_REDIRECT"


@pytest.mark.parametrize("bad", [{"v": 999, "state": "ST_INIT"}, {"v": 1, "state": "NOPE"}, {}])
def test_an_unreadable_stored_session_starts_over(bad):
    service, repo = make()
    repo._items["c1"] = (bad, NOW)
    result = service.handle("c1", "Beine")
    assert result.session_reset is True
    assert repo.get("c1").state is State.ZONE_1  # the broken record was replaced


def test_opt_out_is_stored():
    service, repo = make()
    service.handle("c1", "Beine")
    result = service.handle("c1", "Stopp")
    assert result.session.state is State.OPTOUT and repo.get("c1").state is State.OPTOUT


def test_berlin_now_is_one_or_two_hours_ahead_of_utc():
    offset = berlin_now() - datetime.now(UTC).replace(tzinfo=None)
    assert round(offset.total_seconds() / 3600) in (1, 2)


def test_the_composition_root_works_with_the_default_settings():
    service = build_conversation_service(Settings(database_url=None, wording_provider="none"))
    result = service.handle("c1", "Hallo")
    assert "digitale Assistentin" in texts(result)[0]
