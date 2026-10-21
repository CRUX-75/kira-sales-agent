import pytest

from app.domain.signals import Signals, extract_signals
from app.domain.state_machine import MAX_OBJECTIONS, Session, ambiguous_zones, transition
from app.domain.states import State


def test_one_zone_moves_to_zone_1():
    s = transition(Session(), Signals(zones=("Beine",)))
    assert (s.state, s.zone_1, s.zone_2) == (State.ZONE_1, "Beine", None)


def test_two_zones_in_one_message_move_to_zone_2():
    s = transition(Session(), Signals(zones=("Bauch", "Po")))
    assert (s.state, s.zone_1, s.zone_2) == (State.ZONE_2, "Bauch", "Po")


def test_second_zone_must_differ_from_first():
    s = Session(state=State.ZONE_1, zone_1="Beine")
    assert transition(s, Signals(zones=("Beine",))).state is State.ZONE_1
    assert transition(s, Signals(zones=("Po",))).state is State.ZONE_2


def test_no_signal_never_changes_state():
    """A topic answer (price, hours...) must not move the flow."""
    for state in (State.INIT, State.ZONE_1, State.ZONE_2, State.SLOT_OFFER):
        assert transition(Session(state=state), Signals()).state is state


def test_time_preference_moves_to_slot_offer():
    s = Session(state=State.ZONE_2, zone_1="Beine", zone_2="Po")
    out = transition(s, Signals(time_preference="nachmittags"))
    assert (out.state, out.time_preference) == (State.SLOT_OFFER, "nachmittags")


def test_slot_choice_books():
    s = Session(state=State.SLOT_OFFER, zone_1="Beine", zone_2="Po")
    out = transition(s, Signals(slot_choice=2))
    assert (out.state, out.chosen_slot) == (State.BOOKED, 2)


@pytest.mark.parametrize("state", list(State))
def test_opt_out_wins_from_any_state(state):
    assert transition(Session(state=state), Signals(opt_out=True)).state is State.OPTOUT


def test_opt_out_is_sticky():
    s = Session(state=State.OPTOUT)
    assert transition(s, Signals(zones=("Beine",))).state is State.OPTOUT


def test_handoff_and_terminal_states_do_not_advance():
    for state in (State.HANDOFF, State.BOOKED, State.CLOSED):
        out = transition(Session(state=state), Signals(zones=("Beine",), rejection=True))
        assert out.state is state


def test_handoff_from_flow_state():
    assert transition(Session(state=State.ZONE_1), Signals(handoff=True)).state is State.HANDOFF


def test_rejection_closes():
    assert transition(Session(state=State.ZONE_1), Signals(rejection=True)).state is State.CLOSED


def test_objections_close_after_max_attempts():
    s = Session(state=State.ZONE_1, zone_1="Beine")
    for _ in range(MAX_OBJECTIONS - 1):
        s = transition(s, Signals(objection=True))
        assert s.state is State.ZONE_1
    assert transition(s, Signals(objection=True)).state is State.CLOSED


def test_full_conversation():
    s = Session()
    for message in ["Hallo", "Beine", "Po", "nachmittags", "die zweite"]:
        s = transition(s, extract_signals(message))
    assert (s.state, s.zone_1, s.zone_2, s.time_preference, s.chosen_slot) == (
        State.BOOKED,
        "Beine",
        "Po",
        "nachmittags",
        2,
    )


def test_zones_and_time_window_in_one_message_chain_to_slot_offer():
    s = transition(Session(), Signals(zones=("Beine", "Po"), time_preference="nachmittags"))
    assert (s.state, s.zone_1, s.zone_2, s.time_preference) == (
        State.SLOT_OFFER,
        "Beine",
        "Po",
        "nachmittags",
    )


def test_chain_never_books_in_the_same_turn():
    s = transition(
        Session(), Signals(zones=("Beine", "Po"), time_preference="nachmittags", slot_choice=1)
    )
    assert s.state is State.SLOT_OFFER


def test_three_zones_at_the_start_are_ambiguous_and_nothing_is_captured():
    signals = Signals(zones=("Bauch", "Po", "Arme"))
    out = transition(Session(), signals)
    assert (out.state, out.zone_1, out.zone_2) == (State.INIT, None, None)
    ambiguity = ambiguous_zones(Session(), signals)
    assert (ambiguity.kind, ambiguity.zones) == ("pair", ("Bauch", "Po", "Arme"))


def test_two_new_zones_with_one_already_taken_are_ambiguous():
    session = Session(state=State.ZONE_1, zone_1="Beine")
    signals = Signals(zones=("Po", "Bauch"))
    out = transition(session, signals)
    assert (out.state, out.zone_2) == (State.ZONE_1, None)
    ambiguity = ambiguous_zones(session, signals)
    assert (ambiguity.kind, ambiguity.zones) == ("second", ("Po", "Bauch"))


def test_no_ambiguity_in_normal_cases():
    assert ambiguous_zones(Session(), Signals(zones=("Beine", "Po"))) is None
    assert ambiguous_zones(Session(), Signals()) is None
    zone_1 = Session(state=State.ZONE_1, zone_1="Beine")
    assert ambiguous_zones(zone_1, Signals(zones=("Beine", "Po"))) is None  # one new zone
    assert (
        ambiguous_zones(Session(state=State.ZONE_2), Signals(zones=("Po", "Bauch", "Arme"))) is None
    )
