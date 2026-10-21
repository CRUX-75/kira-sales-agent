from app.domain.validators import (
    human_claims,
    introduced_numbers,
    makes_claims,
    missing_facts,
    validate_style,
)


def test_valid_text():
    assert validate_style("Alles klar. Welche Zone stört dich am meisten?") == ()


def test_violations():
    assert validate_style("") == ("empty",)
    assert "exclamation" in validate_style("Super!")
    assert "emoji" in validate_style("Hallo 😊")
    assert "too_long" in validate_style("a" * 161)
    assert "too_many_sentences" in validate_style("Eins. Zwei. Drei.")


def test_missing_facts():
    assert missing_facts("Ich hätte heute um 14 Uhr.", ("heute um 14 Uhr",)) == ()
    assert missing_facts("Ich hätte morgen.", ("heute um 14 Uhr",)) == ("heute um 14 Uhr",)


def test_introduced_numbers():
    assert introduced_numbers("Um 12 Uhr oder 17 Uhr", "heute um 12 Uhr") == ("17",)
    assert introduced_numbers("Um 12 Uhr", "heute um 12 Uhr") == ()


def test_human_claims():
    assert human_claims("Ich bin ein Mensch")
    assert human_claims("Ich bin keine KI")
    assert human_claims("Ich bin kein Bot")
    assert not human_claims("Ich bin Kira, die digitale Assistentin")


def test_makes_claims():
    assert makes_claims("Bauch und Po passen zusammen")
    assert makes_claims("Die Behandlung ist schmerzfrei")
    assert makes_claims("Sichtbare Ergebnisse schon nach einer Sitzung")
    assert not makes_claims("Welche zweite Zone soll ich dir eintragen?")
