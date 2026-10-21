from datetime import datetime

import pytest

from app.application.planner import plan_turn
from app.domain.slots import Slot
from app.domain.state_machine import Session
from app.domain.states import State
from app.domain.validators import missing_facts, validate_style
from app.infrastructure.kb import load_kb

KB = load_kb()
NOW = datetime(2026, 10, 14, 10, 0)


def intents(plan):
    return [m.intent for m in plan.messages]


def test_greeting_is_verbatim_and_discloses_ai():
    plan = plan_turn(Session(), "Hallo", KB, NOW)
    assert intents(plan) == ["GREETING"]
    assert "digitale Assistentin" in plan.messages[0].text
    assert plan.session.state is State.INIT


def test_zone_leads_to_second_zone_question():
    plan = plan_turn(Session(), "Beine", KB, NOW)
    assert plan.session.state is State.ZONE_1
    assert intents(plan) == ["ASK_ZONE_2"]
    text = plan.messages[0].text
    assert "Beine" in text and "Bauch, Po, Arme oder Rücken" in text


def test_topic_answer_then_resume_pending_question():
    plan = plan_turn(Session(), "Was kostet das?", KB, NOW)
    assert intents(plan) == ["PRICE", "ASK_ZONE_1"]
    assert plan.session.state is State.INIT  # a topic answer never moves the flow


def test_ai_disclosure_is_honest_and_does_not_push():
    plan = plan_turn(Session(), "Bist du ein Bot?", KB, NOW)
    assert intents(plan) == ["AI_DISCLOSURE"]
    assert "KI" in plan.messages[0].text


def test_collision_keeps_deferred_topic():
    plan = plan_turn(Session(), "Wie viel kostet das und wo seid ihr?", KB, NOW)
    assert plan.topic == "PRICE" and "ADDRESS" in plan.deferred


def test_topic_and_zone_in_one_message():
    plan = plan_turn(Session(), "Beine, und was kostet das?", KB, NOW)
    assert intents(plan) == ["PRICE", "ASK_ZONE_2"]
    assert plan.session.state is State.ZONE_1


def test_zones_and_time_in_one_message_go_straight_to_slots():
    plan = plan_turn(Session(), "Beine und Po, nachmittags", KB, NOW)
    assert plan.session.state is State.SLOT_OFFER
    assert len(plan.session.offered_slots) >= 1
    assert intents(plan) == ["OFFER_SLOTS"]


def test_offer_contains_every_offered_slot():
    plan = plan_turn(
        Session(state=State.ZONE_2, zone_1="Beine", zone_2="Po"), "nachmittags", KB, NOW
    )
    message = plan.messages[0]
    assert message.required == tuple(s.label for s in plan.session.offered_slots)
    assert missing_facts(message.text, message.required) == ()


def test_booking_uses_the_offered_slot():
    offered = plan_turn(
        Session(state=State.ZONE_2, zone_1="Beine", zone_2="Po"), "nachmittags", KB, NOW
    )
    booked = plan_turn(offered.session, "die zweite", KB, NOW)
    assert booked.session.state is State.BOOKED
    chosen = offered.session.offered_slots[1].label
    assert chosen in booked.messages[0].text
    assert booked.messages[0].required == (chosen,)


def test_choice_outside_offered_slots_reoffers():
    session = Session(
        state=State.SLOT_OFFER,
        offered_slots=(Slot(NOW.date(), 14, "heute um 14 Uhr"),),
    )
    plan = plan_turn(session, "3", KB, NOW)
    assert plan.session.state is State.SLOT_OFFER
    assert intents(plan) == ["OFFER_SLOTS"]


def test_no_availability_hands_off():
    closed_kb = {**KB, "hours": {day: None for day in KB["hours"]}}
    plan = plan_turn(
        Session(state=State.ZONE_2, zone_1="Beine", zone_2="Po"), "nachmittags", closed_kb, NOW
    )
    assert plan.session.state is State.HANDOFF
    assert intents(plan) == ["HANDOFF"]


def test_opt_out_and_medical_handoff():
    assert intents(
        plan_turn(Session(state=State.ZONE_1), "Bitte keine Nachrichten mehr", KB, NOW)
    ) == ["OPTOUT"]
    medical = plan_turn(Session(state=State.ZONE_1), "Ich bin schwanger", KB, NOW)
    assert medical.session.state is State.HANDOFF and intents(medical) == ["HANDOFF"]


def test_three_objections_close_the_conversation():
    session = Session(state=State.ZONE_1, zone_1="Beine")
    for expected in ("OBJECTION", "OBJECTION"):
        plan = plan_turn(session, "das ist mir zu teuer", KB, NOW)
        assert intents(plan)[0] == expected and plan.session.state is State.ZONE_1
        session = plan.session
    last = plan_turn(session, "das ist mir zu teuer", KB, NOW)
    assert last.session.state is State.CLOSED


def test_unknown_message_gets_redirect_without_state_change():
    plan = plan_turn(Session(state=State.ZONE_1, zone_1="Beine"), "Wie ist das Wetter?", KB, NOW)
    assert intents(plan) == ["OTHER_REDIRECT"]
    assert plan.session.state is State.ZONE_1


def test_topics_still_answered_after_booking():
    booked = Session(
        state=State.BOOKED, offered_slots=(Slot(NOW.date(), 14, "heute um 14 Uhr"),), chosen_slot=1
    )
    plan = plan_turn(booked, "Wo seid ihr?", KB, NOW)
    assert intents(plan) == ["ADDRESS"] and plan.session.state is State.BOOKED
    assert intents(plan_turn(booked, "super danke", KB, NOW)) == ["BOOKED_REMINDER"]


@pytest.mark.parametrize(
    "script",
    [
        ["Hallo", "Beine", "Po", "nachmittags", "die zweite"],
        ["Hey", "Was kostet das?", "Bauch", "Wo seid ihr?", "Rücken", "vormittags", "1"],
        [
            "Bist du ein Bot?",
            "Beine und Arme",
            "das ist mir zu teuer",
            "Wann habt ihr geöffnet?",
            "nachmittags",
        ],
        [
            "Welche Zonen gibt es?",
            "Po",
            "Wie komme ich mit dem Bus zu euch?",
            "Bauch",
            "vormittags",
            "nein danke",
        ],
    ],
)
def test_every_message_passes_style_and_keeps_facts(script):
    session = Session()
    for text in script:
        plan = plan_turn(session, text, KB, NOW)
        session = plan.session
        for message in plan.messages:
            assert validate_style(message.text) == (), (text, message)
            assert missing_facts(message.text, message.required) == ()


def test_zones_are_required_facts_so_an_llm_cannot_change_them():
    first = plan_turn(Session(), "Beine", KB, NOW)
    assert first.messages[0].required == ("Beine", "Bauch", "Po", "Arme", "Rücken")
    second = plan_turn(first.session, "Po", KB, NOW)
    assert second.messages[0].intent == "ASK_TIME"
    assert second.messages[0].required == ("Beine", "Po")
