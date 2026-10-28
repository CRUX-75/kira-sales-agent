from datetime import datetime

import pytest

from app.application.conversation import ConversationService
from app.channels.telegram import (
    Action,
    IncomingMessage,
    conversation_id,
    decide,
    parse_allowed_chat_ids,
    parse_update,
    verify_secret,
)
from app.domain.states import State
from app.infrastructure.kb import load_kb
from app.infrastructure.sessions_memory import InMemorySessionRepository

KB = load_kb()
ALLOWED = frozenset({111})


def update(text="Hallo", chat_type="private", chat_id=111, is_bot=False, update_id=1, **extra):
    message = {
        "chat": {"id": chat_id, "type": chat_type},
        "from": {"id": chat_id, "is_bot": is_bot},
    }
    if text is not None:
        message["text"] = text
    message.update(extra)
    return {"update_id": update_id, "message": message}


# --- parsing -----------------------------------------------------------------------------
def test_a_private_text_message_is_parsed():
    assert parse_update(update("  Hallo  ")) == IncomingMessage(1, 111, "Hallo", "text")


@pytest.mark.parametrize(
    "raw",
    [
        {"update_id": 1},  # no message
        {"update_id": 1, "edited_message": {"chat": {"id": 1, "type": "private"}}},
        {"update_id": 1, "my_chat_member": {}},
        {"message": {"chat": {"id": 1, "type": "private"}, "text": "x"}},  # no update_id
        update(chat_type="group"),
        update(chat_type="supergroup"),
        update(chat_type="channel"),
        update(is_bot=True),  # bots never talk to Kira: no loops, no LLM cost
        {"update_id": 1, "message": {"chat": {"type": "private"}, "text": "x"}},  # no chat id
        {"update_id": 1, "message": {"chat": {"id": True, "type": "private"}, "text": "x"}},
        {"update_id": 1, "message": "garbage"},
    ],
)
def test_everything_that_is_not_a_private_human_message_is_ignored(raw):
    assert parse_update(raw) is None


@pytest.mark.parametrize(
    "extra", [{"photo": [{}]}, {"voice": {}}, {"sticker": {}}, {"document": {}}]
)
def test_content_without_text_is_marked_unsupported(extra):
    parsed = parse_update(update(text=None, **extra))
    assert (parsed.kind, parsed.text) == ("unsupported", None)


def test_whitespace_only_text_is_unsupported():
    assert parse_update(update("   ")).kind == "unsupported"


# --- access policy -----------------------------------------------------------------------
def test_allowed_chat_text_goes_to_the_conversation():
    action = decide(parse_update(update("Beine")), ALLOWED, KB)
    assert action == Action("converse", "Beine")


def test_start_and_stop_commands_map_to_greeting_and_opt_out():
    for command, expected in (
        ("/start", "Hallo"),
        ("/start promo", "Hallo"),
        ("/START", "Hallo"),
        ("/start@kira_genflow_demo_bot", "Hallo"),
        ("/stop", "Stopp"),
    ):
        assert decide(parse_update(update(command)), ALLOWED, KB) == Action("converse", expected)


def test_unknown_commands_are_just_text():
    assert decide(parse_update(update("/foo")), ALLOWED, KB) == Action("converse", "/foo")


def test_strangers_get_a_fixed_reply_and_never_reach_the_conversation():
    action = decide(parse_update(update("Hallo", chat_id=999)), ALLOWED, KB)
    assert action == Action("reply", KB["templates"]["CHANNEL_NOT_ALLOWED"])


def test_an_empty_allowlist_means_nobody():
    assert decide(parse_update(update("Hallo")), frozenset(), KB).kind == "reply"


def test_id_works_for_anyone_and_reveals_only_their_own_id():
    for chat_id, allowed in ((999, ALLOWED), (111, ALLOWED), (5, frozenset())):
        action = decide(parse_update(update("/id", chat_id=chat_id)), allowed, KB)
        assert action.kind == "reply" and str(chat_id) in action.text


def test_unsupported_content_gets_a_fixed_reply_only_from_allowed_chats():
    raw = update(text=None, photo=[{}])
    assert decide(parse_update(raw), ALLOWED, KB) == Action(
        "reply", KB["templates"]["CHANNEL_UNSUPPORTED"]
    )
    stranger = update(text=None, photo=[{}], chat_id=999)
    assert (
        decide(parse_update(stranger), ALLOWED, KB).text == KB["templates"]["CHANNEL_NOT_ALLOWED"]
    )


def test_ignored_updates_produce_no_action():
    assert decide(None, ALLOWED, KB) == Action("ignore")


def test_the_stop_command_really_opts_out_through_the_conversation_service():
    repo = InMemorySessionRepository()
    service = ConversationService(repo, KB, clock=lambda: datetime(2026, 10, 14, 10, 0))
    service.handle("c1", decide(parse_update(update("Beine")), ALLOWED, KB).text)
    service.handle("c1", decide(parse_update(update("/stop")), ALLOWED, KB).text)
    assert repo.get("c1").state is State.OPTOUT


# --- webhook secret ----------------------------------------------------------------------
def test_verify_secret():
    assert verify_secret("s3cret", "s3cret")
    assert not verify_secret("other", "s3cret")
    assert not verify_secret(None, "s3cret")
    assert not verify_secret("", "")  # no secret configured: reject everything
    assert not verify_secret("anything", "")


# --- anonymous conversation id -----------------------------------------------------------
def test_conversation_id_is_stable_keyed_and_hides_the_chat_id():
    first = conversation_id(123456789, "key-a")
    assert first == conversation_id(123456789, "key-a")
    assert first != conversation_id(123456789, "key-b")
    assert first != conversation_id(987654321, "key-a")
    assert "123456789" not in first and first.startswith("tg_") and len(first) == 35


def test_conversation_id_requires_a_secret():
    with pytest.raises(ValueError, match="CONVERSATION_ID_SECRET"):
        conversation_id(1, "")


# --- allowlist configuration -------------------------------------------------------------
def test_parse_allowed_chat_ids():
    assert parse_allowed_chat_ids("1, 2 ,3,") == frozenset({1, 2, 3})
    assert parse_allowed_chat_ids("") == frozenset()
    assert parse_allowed_chat_ids("-1001") == frozenset({-1001})


def test_a_typo_in_the_allowlist_fails_loudly():
    with pytest.raises(ValueError, match="abc"):
        parse_allowed_chat_ids("1,abc")
