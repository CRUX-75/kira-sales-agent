from app.domain.validators import missing_facts, validate_style


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
