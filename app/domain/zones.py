"""Deterministic zone detection: closed whitelist plus aliases."""
import re

CANONICAL_ZONES = ("Bauch", "Beine", "Po", "Arme", "Rücken")

_ALIASES = (
    (re.compile(r"\bbauch(bereich)?\b"), "Bauch"),
    (re.compile(r"\b(beine|oberschenkel|waden)\b"), "Beine"),
    (re.compile(r"\b(po|popo|gesäß|gesaess|hintern)\b"), "Po"),
    (re.compile(r"\b(arme|oberarme)\b"), "Arme"),
    (re.compile(r"\b(rücken|ruecken|rucken)\b"), "Rücken"),
)


def detect_zones(text: str) -> tuple[str, ...]:
    """Return canonical zones in order of appearance, without duplicates."""
    lowered = text.lower()
    hits: list[tuple[int, str]] = []
    for pattern, zone in _ALIASES:
        match = pattern.search(lowered)
        if match:
            hits.append((match.start(), zone))
    hits.sort()
    ordered: list[str] = []
    for _, zone in hits:
        if zone not in ordered:
            ordered.append(zone)
    return tuple(ordered)
