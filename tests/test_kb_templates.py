"""Every verbatim template in the KB must satisfy the style rules."""

from app.domain.validators import validate_style
from app.domain.zones import CANONICAL_ZONES
from app.infrastructure.kb import load_kb

KB = load_kb()


def _flat_templates():
    for name, value in KB["templates"].items():
        for text in value if isinstance(value, list) else [value]:
            yield name, text


def test_all_templates_pass_style():
    failures = {}
    for name, text in _flat_templates():
        rendered = text.format(
            zone_1="Beine",
            zone_2="Po",
            options="Bauch, Po, Arme oder Rücken",
            slot="am Donnerstag um 13 Uhr",
            slot_list="heute um 12 Uhr, am Donnerstag um 13 Uhr oder am Dienstag um 16 Uhr",
        )
        violations = validate_style(rendered)
        if violations:
            failures[name] = violations
    assert not failures, failures


def test_kb_zones_match_domain_whitelist():
    assert tuple(KB["zones"]) == CANONICAL_ZONES


def test_kb_is_marked_fictional():
    assert KB["meta"]["fictional"] is True


def test_ai_disclosure_template_says_it_is_an_ai():
    text = KB["templates"]["AI_DISCLOSURE"].lower()
    assert "ki" in text and "digitale assistentin" in text
    assert "digitale assistentin" in KB["templates"]["GREETING"].lower()
