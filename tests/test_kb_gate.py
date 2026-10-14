import pytest

from app.domain.kb_gate import match_topic


@pytest.mark.parametrize(
    "text,topic",
    [
        ("Was kostet das?", "PRICE"),
        ("Wie teuer ist das?", "PRICE"),
        ("Das ist mir zu teuer", "OBJECTION"),  # "zu teuer" is an objection, not a price question
        ("Bist du ein Bot?", "AI_DISCLOSURE"),
        ("Schreibe ich mit einem Menschen?", "AI_DISCLOSURE"),
        ("Stopp", "OPTOUT"),
        ("Wann habt ihr geöffnet?", "HOURS"),
        ("Wie komme ich mit der Bahn zu euch? Gibt es einen Bus?", "TRANSIT"),
        ("Wo seid ihr?", "ADDRESS"),
        ("Welche Zonen gibt es?", "ZONES"),
        ("Hallo", "GREETING"),
    ],
)
def test_topics(text, topic):
    result = match_topic(text)
    assert result.topic == topic
    assert result.kb_hit


def test_collision_priority_and_deferred():
    result = match_topic("Wie viel kostet das und wo seid ihr?")
    assert result.topic == "PRICE"
    assert "ADDRESS" in result.deferred


def test_ai_disclosure_outranks_everything():
    result = match_topic("Bist du ein Bot und was kostet das?")
    assert result.topic == "AI_DISCLOSURE"
    assert "PRICE" in result.deferred


def test_zone_names_are_slot_filling_not_a_topic():
    result = match_topic("Beine")
    assert (result.topic, result.kb_hit) == ("OTHER", False)


def test_other_is_fallback_only():
    result = match_topic("Wie ist das Wetter?")
    assert (result.topic, result.kb_hit, result.deferred) == ("OTHER", False, ())
