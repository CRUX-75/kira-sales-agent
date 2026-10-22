"""Session <-> JSON-safe dict. Versioned so stored sessions survive future changes."""

from datetime import date
from typing import Any

from app.domain.slots import Slot
from app.domain.state_machine import Session
from app.domain.states import State

SCHEMA_VERSION = 1


def session_to_dict(session: Session) -> dict[str, Any]:
    return {
        "v": SCHEMA_VERSION,
        "state": session.state.value,
        "zone_1": session.zone_1,
        "zone_2": session.zone_2,
        "time_preference": session.time_preference,
        "chosen_slot": session.chosen_slot,
        "objection_count": session.objection_count,
        "offered_slots": [
            {"day": slot.day.isoformat(), "hour": slot.hour, "label": slot.label}
            for slot in session.offered_slots
        ],
    }


def session_from_dict(data: dict[str, Any]) -> Session:
    version = data.get("v")
    if version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported session schema version: {version!r}")
    return Session(
        state=State(data["state"]),
        zone_1=data.get("zone_1"),
        zone_2=data.get("zone_2"),
        time_preference=data.get("time_preference"),
        chosen_slot=data.get("chosen_slot"),
        objection_count=data.get("objection_count", 0),
        offered_slots=tuple(
            Slot(date.fromisoformat(slot["day"]), slot["hour"], slot["label"])
            for slot in data.get("offered_slots", [])
        ),
    )
