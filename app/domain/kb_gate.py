"""KB Gate: deterministic topic detection. Lower priority number wins."""
import re
from dataclasses import dataclass

from .signals import OBJECTION_RE, OPT_OUT_RE


@dataclass(frozen=True)
class Topic:
    name: str
    priority: int
    pattern: re.Pattern[str]


TOPICS = (
    Topic(
        "AI_DISCLOSURE",
        0,
        re.compile(
            r"bist du (ein |eine )?(bot|roboter|ki|mensch|echt|echter mensch)"
            r"|chatbot|künstliche intelligenz"
            r"|mit (einem|einer) (bot|ki|menschen|maschine|echten person)"
        ),
    ),
    Topic("OPTOUT", 0, OPT_OUT_RE),
    Topic(
        "PRICE",
        1,
        re.compile(r"\bpreis\w*|\bkosten\b|\bkostet\b|wie ?viel|(?<!zu )\bteuer\b|\beuro\b"),
    ),
    Topic("ZONES", 2, re.compile(r"welche (körper)?(zonen|bereiche)|zonen (gibt|habt|hast)")),
    Topic("ADDRESS", 3, re.compile(r"adresse|wo seid ihr|wo befindet|wo ist das|standort")),
    Topic("HOURS", 4, re.compile(r"öffnungszeiten|geöffnet|wann .*offen")),
    Topic("TRANSIT", 5, re.compile(r"öpnv|u-?bahn|\btram\b|\bbus\b|anfahrt|wie komme ich|öffentlich")),
    Topic("BOOKING", 6, re.compile(r"termin (machen|buchen|vereinbaren)|einen termin|\bbuchen\b")),
    Topic("OBJECTION", 7, OBJECTION_RE),
    Topic(
        "GREETING",
        8,
        re.compile(r"^\s*(hallo|hi|hey|moin|servus|guten (tag|morgen|abend))\b"),
    ),
)


@dataclass(frozen=True)
class GateResult:
    topic: str
    kb_hit: bool
    deferred: tuple[str, ...] = ()


def match_topic(text: str) -> GateResult:
    """Answer only the highest-priority topic; keep the others for follow-up."""
    lowered = text.lower()
    matches = [t for t in TOPICS if t.pattern.search(lowered)]
    if not matches:
        return GateResult(topic="OTHER", kb_hit=False)
    matches.sort(key=lambda t: t.priority)
    return GateResult(
        topic=matches[0].name, kb_hit=True, deferred=tuple(t.name for t in matches[1:])
    )
