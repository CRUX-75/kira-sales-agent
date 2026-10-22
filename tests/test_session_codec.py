import json
from datetime import date

import pytest

from app.application.session_codec import SCHEMA_VERSION, session_from_dict, session_to_dict
from app.domain.slots import Slot
from app.domain.state_machine import Session
from app.domain.states import State

FULL = Session(
    state=State.SLOT_OFFER,
    zone_1="Beine",
    zone_2="Po",
    time_preference="nachmittags",
    chosen_slot=None,
    objection_count=2,
    offered_slots=(
        Slot(date(2026, 10, 14), 13, "heute um 13 Uhr"),
        Slot(date(2026, 10, 15), 15, "morgen um 15 Uhr"),
    ),
)


def test_round_trip_keeps_everything():
    assert session_from_dict(session_to_dict(FULL)) == FULL


def test_the_dict_is_json_serialisable():
    assert session_from_dict(json.loads(json.dumps(session_to_dict(FULL)))) == FULL


@pytest.mark.parametrize("state", list(State))
def test_every_state_round_trips(state):
    session = Session(state=state)
    assert session_from_dict(session_to_dict(session)).state is state


def test_a_default_session_round_trips():
    assert session_from_dict(session_to_dict(Session())) == Session()


def test_unknown_schema_version_is_rejected():
    data = session_to_dict(FULL) | {"v": SCHEMA_VERSION + 1}
    with pytest.raises(ValueError, match="schema version"):
        session_from_dict(data)


def test_missing_optional_fields_use_defaults():
    out = session_from_dict({"v": SCHEMA_VERSION, "state": "ST_INIT"})
    assert out == Session()
