"""Pure state machine. No I/O, no LLM. Priority: opt-out > handoff > rejection > flow."""

from dataclasses import dataclass, replace

from .signals import Signals
from .slots import Slot
from .states import TERMINAL_STATES, State

MAX_OBJECTIONS = 3


@dataclass(frozen=True)
class Session:
    state: State = State.INIT
    zone_1: str | None = None
    zone_2: str | None = None
    time_preference: str | None = None
    chosen_slot: int | None = None
    objection_count: int = 0
    offered_slots: tuple[Slot, ...] = ()


def transition(session: Session, signals: Signals) -> Session:
    if signals.opt_out:
        return replace(session, state=State.OPTOUT)  # wins from any state
    if session.state is State.OPTOUT:
        return session
    if signals.handoff:
        return replace(session, state=State.HANDOFF)
    if session.state in TERMINAL_STATES:
        return session
    if signals.rejection:
        return replace(session, state=State.CLOSED)
    if signals.objection:
        session = replace(session, objection_count=session.objection_count + 1)
        if session.objection_count >= MAX_OBJECTIONS:
            return replace(session, state=State.CLOSED)
    advanced = _advance(session, signals)
    # Zones and time window may arrive in one message, but never chain into a booking.
    while advanced.state in (State.ZONE_1, State.ZONE_2):
        following = _advance(advanced, signals)
        if following == advanced:
            break
        advanced = following
    return advanced


def _advance(session: Session, signals: Signals) -> Session:
    state = session.state
    if state is State.INIT:
        if len(signals.zones) >= 3:  # more than the offer includes: ambiguous, ask first
            return session
        if len(signals.zones) >= 2:
            return replace(
                session, state=State.ZONE_2, zone_1=signals.zones[0], zone_2=signals.zones[1]
            )
        if len(signals.zones) == 1:
            return replace(session, state=State.ZONE_1, zone_1=signals.zones[0])
        return session
    if state is State.ZONE_1:
        new = [z for z in signals.zones if z != session.zone_1]
        if len(new) == 1:  # several new zones are ambiguous: ask first
            return replace(session, state=State.ZONE_2, zone_2=new[0])
        return session
    if state is State.ZONE_2:
        if signals.time_preference:
            return replace(session, state=State.SLOT_OFFER, time_preference=signals.time_preference)
        return session
    if state is State.SLOT_OFFER:
        if signals.slot_choice is not None:
            return replace(session, state=State.BOOKED, chosen_slot=signals.slot_choice)
        if signals.time_preference:
            return replace(session, time_preference=signals.time_preference)
        return session
    return session


@dataclass(frozen=True)
class ZoneAmbiguity:
    kind: str  # "second": one zone is taken and several candidates were named; "pair": 3+ named
    zones: tuple[str, ...]


def ambiguous_zones(session: Session, signals: Signals) -> ZoneAmbiguity | None:
    """Zones the customer named that do not fit the offer (two zones): ask, never guess."""
    if session.state is State.INIT and len(signals.zones) >= 3:
        return ZoneAmbiguity("pair", signals.zones)
    if session.state is State.ZONE_1:
        new = tuple(z for z in signals.zones if z != session.zone_1)
        if len(new) >= 2:
            return ZoneAmbiguity("second", new)
    return None
