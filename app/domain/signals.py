"""Deterministic signal extraction from a user message."""

import re
from dataclasses import dataclass

from .zones import detect_zones

OPT_OUT_RE = re.compile(
    r"\b(stopp?|unsubscribe|abmelden|austragen)\b"
    r"|keine (weiteren )?nachrichten mehr"
    r"|nicht mehr (schreiben|anschreiben)"
    r"|schreib(t)? mir nicht mehr"
)
REJECTION_RE = re.compile(r"nein danke|kein interesse|nicht interessiert|lass mal|ne danke")
OBJECTION_RE = re.compile(
    r"zu teuer|kein geld|keine zeit|nicht sicher|muss (ich )?(noch )?überlegen|vielleicht später"
)
HANDOFF_RE = re.compile(
    r"(mit|zu) (einem|einer) (mitarbeiter(in)?|menschen|person) (sprechen|reden|schreiben)"
    r"|mitarbeiter(in)? sprechen|echte(n|r)? (person|mensch)\b"
)
MEDICAL_RE = re.compile(
    r"schwanger|stillzeit|\bstille\b|diabetes|medikament|krankheit|erkrankung|\barzt\b|thrombose|operation"
)
_MORNING_RE = re.compile(r"\b(vormittags?|morgens|früh|frueh)\b")
_AFTERNOON_RE = re.compile(r"\b(nachmittags?|mittags?|abends?)\b")
_ORDINALS = {"erste": 1, "zweite": 2, "dritte": 3}


@dataclass(frozen=True)
class Signals:
    opt_out: bool = False
    handoff: bool = False
    rejection: bool = False
    objection: bool = False
    zones: tuple[str, ...] = ()
    time_preference: str | None = None
    slot_choice: int | None = None


def detect_time_preference(text: str) -> str | None:
    lowered = text.lower()
    morning = bool(_MORNING_RE.search(lowered))
    afternoon = bool(_AFTERNOON_RE.search(lowered))
    if morning == afternoon:  # none, or ambiguous
        return None
    return "vormittags" if morning else "nachmittags"


def detect_slot_choice(text: str) -> int | None:
    lowered = text.lower().strip()
    match = re.search(r"\b(erste|zweite|dritte)(n|r)?\b", lowered)
    if match:
        return _ORDINALS[match.group(1)]
    match = re.fullmatch(r"(?:option\s*)?([123])\.?", lowered)
    if match:
        return int(match.group(1))
    return None


def extract_signals(text: str) -> Signals:
    lowered = text.lower()
    return Signals(
        opt_out=bool(OPT_OUT_RE.search(lowered)),
        handoff=bool(HANDOFF_RE.search(lowered) or MEDICAL_RE.search(lowered)),
        rejection=bool(REJECTION_RE.search(lowered)),
        objection=bool(OBJECTION_RE.search(lowered)),
        zones=detect_zones(text),
        time_preference=detect_time_preference(text),
        slot_choice=detect_slot_choice(text),
    )
