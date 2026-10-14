import pytest

from app.domain.signals import (
    detect_slot_choice,
    detect_time_preference,
    extract_signals,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("nachmittags", "nachmittags"),
        ("vormittags", "vormittags"),  # regression: "mittag" must not match inside "vormittag"
        ("eher vormittag", "vormittags"),
        ("abends", "nachmittags"),
        ("vormittag oder nachmittag", None),  # ambiguous
        ("morgen", None),  # "tomorrow", not "morning"
    ],
)
def test_time_preference(text, expected):
    assert detect_time_preference(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [("die zweite", 2), ("3", 3), ("Option 1", 1), ("Beine", None), ("ich nehme die erste", 1)],
)
def test_slot_choice(text, expected):
    assert detect_slot_choice(text) == expected


def test_opt_out():
    assert extract_signals("Bitte keine Nachrichten mehr").opt_out
    assert extract_signals("stop").opt_out
    assert not extract_signals("Beine bitte").opt_out


def test_rejection_and_objection_are_distinct():
    assert extract_signals("nein danke").rejection
    assert extract_signals("das ist mir zu teuer").objection
    assert not extract_signals("das ist mir zu teuer").rejection


def test_handoff_for_medical_or_human_request():
    assert extract_signals("Ich bin schwanger").handoff
    assert extract_signals("Ich möchte mit einem Menschen sprechen").handoff
    assert not extract_signals("Bist du ein Bot?").handoff
