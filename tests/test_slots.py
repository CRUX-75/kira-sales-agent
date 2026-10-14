from datetime import datetime

from app.domain.slots import generate_slots, parse_hours
from app.infrastructure.kb import load_kb

HOURS = load_kb()["hours"]
WEDNESDAY_10 = datetime(2026, 10, 14, 10, 0)  # a Wednesday


def test_parse_hours():
    assert parse_hours("09:00-17:00") == (9, 17)
    assert parse_hours(None) is None


def test_max_three_slots_on_different_days():
    slots = generate_slots(WEDNESDAY_10, "nachmittags", HOURS)
    assert 1 <= len(slots) <= 3
    assert len({s.day for s in slots}) == len(slots)


def test_afternoon_and_morning_preferences_are_respected():
    assert all(s.hour >= 12 for s in generate_slots(WEDNESDAY_10, "nachmittags", HOURS))
    assert all(s.hour < 12 for s in generate_slots(WEDNESDAY_10, "vormittags", HOURS))


def test_slots_stay_inside_opening_hours_and_skip_closed_days():
    for preference in ("vormittags", "nachmittags"):
        for slot in generate_slots(WEDNESDAY_10, preference, HOURS):
            assert slot.day.weekday() not in (5, 6)  # Saturday and Sunday are closed
            assert slot.hour <= 17  # latest start across the week: Mo/Di close 17, Mi/Do 19


def test_friday_last_start_is_one_hour_before_closing():
    friday = datetime(2026, 10, 16, 8, 0)
    slots = generate_slots(friday, "nachmittags", HOURS, max_slots=10)
    todays = [s for s in slots if s.day == friday.date()]
    assert todays and max(s.hour for s in todays) <= 14  # Friday closes at 15


def test_lead_time_for_today():
    late = datetime(2026, 10, 14, 17, 0)  # 17:00 + 2h lead = 19:00 -> nothing left today
    assert all(s.day != late.date() for s in generate_slots(late, "nachmittags", HOURS))


def test_labels_follow_format_rules():
    labels = [s.label for s in generate_slots(WEDNESDAY_10, "nachmittags", HOURS)]
    assert labels[0].startswith("heute um ")
    for label in labels:
        assert "2026" not in label  # never mention the year
        assert label.endswith(" Uhr")
    assert any(label.startswith("am ") for label in labels)


def test_tomorrow_label():
    evening = datetime(2026, 10, 14, 18, 0)  # nothing today -> first slot tomorrow
    first = generate_slots(evening, "nachmittags", HOURS)[0]
    assert first.label.startswith("morgen um ")


def test_no_slots_when_closed_all_week():
    closed = {day: None for day in HOURS}
    assert generate_slots(WEDNESDAY_10, "nachmittags", closed) == ()
