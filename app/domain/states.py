"""Conversation states. States are never inferred by the LLM."""
from enum import StrEnum


class State(StrEnum):
    INIT = "ST_INIT"
    ZONE_1 = "ST_ZONE_1"
    ZONE_2 = "ST_ZONE_2"  # both zones captured, time-window question pending
    SLOT_OFFER = "ST_SLOT_OFFER"
    BOOKED = "ST_BOOKED"  # booking *request* registered, a human confirms
    CLOSED = "ST_CLOSED"
    OPTOUT = "ST_OPTOUT"
    HANDOFF = "ST_HANDOFF"


TERMINAL_STATES = frozenset({State.BOOKED, State.CLOSED, State.OPTOUT, State.HANDOFF})
