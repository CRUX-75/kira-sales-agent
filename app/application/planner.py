"""Turn planner: (session, user text) -> new session + messages to send.

Pure and deterministic. It decides WHAT is said. Each Message carries a deterministic
`text` that is always valid; the LLM may only reword messages marked "constrained",
and must keep every string in `required` (slots, prices...).
"""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from app.domain.kb_gate import GateResult, match_topic
from app.domain.signals import Signals, extract_signals
from app.domain.slots import generate_slots
from app.domain.state_machine import Session, ZoneAmbiguity, ambiguous_zones, transition
from app.domain.states import TERMINAL_STATES, State
from app.domain.zones import CANONICAL_ZONES

ANSWER_TOPICS = frozenset({"PRICE", "ADDRESS", "HOURS", "TRANSIT"})  # verbatim KB answers


@dataclass(frozen=True)
class Message:
    intent: str
    text: str
    wording: str  # "verbatim" | "constrained"
    required: tuple[str, ...] = ()


@dataclass(frozen=True)
class TurnPlan:
    session: Session
    messages: tuple[Message, ...]
    topic: str
    deferred: tuple[str, ...] = ()


def _join_or(items) -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " oder " + items[-1]


def _tpl(kb: dict[str, Any], key: str, wording: str, required=(), **fmt) -> Message:
    return Message(key, kb["templates"][key].format(**fmt), wording, tuple(required))


def _topic_answer(gate: GateResult, kb: dict[str, Any]) -> Message | None:
    if gate.kb_hit and gate.topic in ANSWER_TOPICS:
        return _tpl(kb, gate.topic, "verbatim")
    return None


def _pending_message(session: Session, kb: dict[str, Any]) -> Message:
    state = session.state
    if state is State.INIT:
        return _tpl(kb, "ASK_ZONE_1", "constrained")
    if state is State.ZONE_1:
        remaining = [z for z in CANONICAL_ZONES if z != session.zone_1]
        options = _join_or(remaining)
        required = (session.zone_1, *remaining)
        return _tpl(
            kb, "ASK_ZONE_2", "constrained", required, zone_1=session.zone_1, options=options
        )
    if state is State.ZONE_2:
        required = (session.zone_1, session.zone_2)
        return _tpl(
            kb, "ASK_TIME", "constrained", required, zone_1=session.zone_1, zone_2=session.zone_2
        )
    labels = tuple(slot.label for slot in session.offered_slots)
    return _tpl(kb, "OFFER_SLOTS", "constrained", required=labels, slot_list=_join_or(labels))


def _terminal_messages(
    before: Session, after: Session, signals: Signals, gate: GateResult, kb: dict[str, Any]
) -> tuple[Message, ...]:
    state = after.state
    if state is State.OPTOUT:
        return (_tpl(kb, "OPTOUT", "verbatim"),)
    if state is State.HANDOFF:
        return (_tpl(kb, "HANDOFF", "verbatim"),)
    already = before.state is state
    answer = _topic_answer(gate, kb)
    if state is State.CLOSED:
        if already and answer:
            return (answer,)
        if signals.objection and not signals.rejection:
            return (Message("OBJECTION", kb["templates"]["OBJECTION"][-1], "constrained"),)
        return (_tpl(kb, "REJECTION_CLOSE", "verbatim"),)
    # BOOKED
    if already:
        return (answer,) if answer else (_tpl(kb, "BOOKED_REMINDER", "verbatim"),)
    slot = after.offered_slots[after.chosen_slot - 1].label
    return (_tpl(kb, "BOOKED", "constrained", required=(slot,), slot=slot),)


def _clarification(ambiguity: ZoneAmbiguity, session: Session, kb: dict[str, Any]) -> Message:
    options = _join_or(ambiguity.zones)
    if ambiguity.kind == "pair":
        return _tpl(kb, "CLARIFY_PAIR", "constrained", ambiguity.zones, options=options)
    required = (session.zone_1, *ambiguity.zones)
    return _tpl(
        kb, "CLARIFY_SECOND", "constrained", required, zone_1=session.zone_1, options=options
    )


def _flow_messages(
    before: Session,
    after: Session,
    gate: GateResult,
    kb: dict[str, Any],
    reoffer: bool,
    ambiguity: ZoneAmbiguity | None = None,
) -> tuple[Message, ...]:
    progressed = after != before or reoffer or ambiguity is not None
    topic = gate.topic if gate.kb_hit else None
    if topic == "AI_DISCLOSURE":  # honest answer, no pushing back into the funnel
        return (_tpl(kb, "AI_DISCLOSURE", "verbatim"),)
    if topic == "GREETING" and after.state is State.INIT and not progressed:
        return (_tpl(kb, "GREETING", "verbatim"),)  # already contains the first question
    messages: list[Message] = []
    if topic in ANSWER_TOPICS:
        messages.append(_tpl(kb, topic, "verbatim"))
    elif topic == "ZONES":
        messages.append(_tpl(kb, "ZONES_LIST", "constrained", options=_join_or(CANONICAL_ZONES)))
    elif topic == "OBJECTION":
        index = min(max(after.objection_count, 1), 3) - 1
        messages.append(Message("OBJECTION", kb["templates"]["OBJECTION"][index], "constrained"))
    elif topic is None and not progressed:
        return (_tpl(kb, "OTHER_REDIRECT", "constrained"),)
    messages.append(
        _clarification(ambiguity, after, kb) if ambiguity else _pending_message(after, kb)
    )
    return tuple(messages)


def plan_turn(session: Session, text: str, kb: dict[str, Any], now: datetime) -> TurnPlan:
    signals = extract_signals(text)
    gate = match_topic(text)
    new = transition(session, signals)

    reoffer = False
    if new.state is State.BOOKED and session.state is not State.BOOKED:
        choice = new.chosen_slot
        if choice is None or not 1 <= choice <= len(new.offered_slots):
            new, reoffer = session, True  # the user picked a slot that was never offered

    if new.state is State.SLOT_OFFER and (
        session.state is not State.SLOT_OFFER or new.time_preference != session.time_preference
    ):
        slots = generate_slots(now, new.time_preference, kb["hours"])
        new = replace(new, offered_slots=slots) if slots else replace(new, state=State.HANDOFF)

    if new.state in TERMINAL_STATES:
        messages = _terminal_messages(session, new, signals, gate, kb)
    else:
        ambiguity = ambiguous_zones(session, signals) if new.state is session.state else None
        messages = _flow_messages(session, new, gate, kb, reoffer, ambiguity)
    return TurnPlan(session=new, messages=messages, topic=gate.topic, deferred=gate.deferred)
