"""Deterministic slot generation from the KB opening-hours table.

Rules: max 3 slots, spread over different days, inside opening hours, matching the
morning / afternoon preference, at least LEAD_HOURS from now, weekday + time, no year.
Opening hours are read as full hours ("09:00-17:00" -> 9 to 17).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

WEEKDAYS_DE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
MAX_SLOTS = 3
LEAD_HOURS = 2
TREATMENT_HOURS = 1
HORIZON_DAYS = 7  # offsets 0..6, so a weekday name is never ambiguous


@dataclass(frozen=True)
class Slot:
    day: date
    hour: int
    label: str  # frozen at offer time, e.g. "am Mittwoch um 15 Uhr"


def parse_hours(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    start, end = value.split("-")
    return int(start.split(":")[0]), int(end.split(":")[0])


def _label(day: date, hour: int, today: date) -> str:
    if day == today:
        return f"heute um {hour} Uhr"
    if day == today + timedelta(days=1):
        return f"morgen um {hour} Uhr"
    return f"am {WEEKDAYS_DE[day.weekday()]} um {hour} Uhr"


def _candidate_hours(day_hours: tuple[int, int], preference: str | None) -> list[int]:
    open_hour, close_hour = day_hours
    last_start = close_hour - TREATMENT_HOURS
    hours = range(open_hour, last_start + 1)
    if preference == "vormittags":
        return [h for h in hours if h < 12]
    return [h for h in hours if h >= 12]


def generate_slots(
    now: datetime,
    preference: str | None,
    hours: Mapping[str, str | None],
    *,
    max_slots: int = MAX_SLOTS,
) -> tuple[Slot, ...]:
    earliest = now + timedelta(hours=LEAD_HOURS)
    options: list[tuple[date, list[int]]] = []
    for offset in range(HORIZON_DAYS):
        day = now.date() + timedelta(days=offset)
        day_hours = parse_hours(hours.get(WEEKDAYS_DE[day.weekday()]))
        if not day_hours:
            continue
        candidates = [
            h
            for h in _candidate_hours(day_hours, preference)
            if datetime.combine(day, time(h)) >= earliest
        ]
        if candidates:
            options.append((day, candidates))

    # Spread over days: every other available day first, then fill up in order.
    picked = options[::2][:max_slots]
    for option in options:
        if len(picked) >= max_slots:
            break
        if option not in picked:
            picked.append(option)
    picked.sort(key=lambda option: option[0])

    slots: list[Slot] = []
    for index, (day, candidates) in enumerate(picked):
        position = (0, (len(candidates) - 1) // 2, len(candidates) - 1)[index % 3]
        hour = candidates[position]
        slots.append(Slot(day=day, hour=hour, label=_label(day, hour, now.date())))
    return tuple(slots)
