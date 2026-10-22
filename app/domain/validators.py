"""Style validator. Style is enforced by code, not by the prompt."""

import re

_EMOJI_RE = re.compile("[\U0001f300-\U0001faff\u2600-\u27bf\u2b50\ufe0f]")


def validate_style(text: str, *, max_chars: int = 160, max_sentences: int = 2) -> tuple[str, ...]:
    """Return a tuple of violation codes. Empty tuple means the text is valid."""
    violations: list[str] = []
    stripped = text.strip()
    if not stripped:
        return ("empty",)
    if len(stripped) > max_chars:
        violations.append("too_long")
    sentences = [s for s in re.split(r"(?<=[.?!])\s+", stripped) if s.strip()]
    if len(sentences) > max_sentences:
        violations.append("too_many_sentences")
    if _EMOJI_RE.search(stripped):
        violations.append("emoji")
    if "!" in stripped:
        violations.append("exclamation")
    return tuple(violations)


def missing_facts(text: str, required: tuple[str, ...]) -> tuple[str, ...]:
    """Facts (slots, prices...) that must survive any LLM rewording."""
    return tuple(fact for fact in required if fact not in text)


_DIGITS_RE = re.compile(r"\d+")
_HUMAN_CLAIM_RE = re.compile(
    r"\bich bin (ein |eine )?(mensch|echte[rn]? mensch|echt)\b|\bkeine ki\b|\bkein (bot|roboter)\b"
)


def introduced_numbers(candidate: str, allowed_text: str) -> tuple[str, ...]:
    """Numbers in `candidate` that do not appear in `allowed_text` (prices, hours, dates...)."""
    allowed = set(_DIGITS_RE.findall(allowed_text))
    found = dict.fromkeys(_DIGITS_RE.findall(candidate))
    return tuple(number for number in found if number not in allowed)


def human_claims(text: str) -> bool:
    """True if the text claims to be a human or denies being an AI."""
    return bool(_HUMAN_CLAIM_RE.search(text.lower()))


_CLAIM_RE = re.compile(
    r"\b(ergebnis\w*|wirkt|wirkung\w*|wirksam\w*|garantie\w*|garantiert|nebenwirkung\w*"
    r"|schmerz\w*|effektiv\w*|abnehm\w*|kleidergr\w*|cellulite|straff\w*|heilt|heilung"
    r"|passen (gut )?zusammen)\b"
)


def makes_claims(text: str) -> bool:
    """Vocabulary of treatment, result or health claims. A cheap net, not a full detector."""
    return bool(_CLAIM_RE.search(text.lower()))
