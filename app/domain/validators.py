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
