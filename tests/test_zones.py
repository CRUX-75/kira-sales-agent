import pytest

from app.domain.zones import detect_zones


@pytest.mark.parametrize(
    "text,expected",
    [
        ("beine", ("Beine",)),
        ("Bauch und Po", ("Bauch", "Po")),
        ("po und bauch", ("Po", "Bauch")),  # order of appearance
        ("Bauchschmerzen", ()),  # no partial-word matches
        ("ruecken", ("Rücken",)),
        ("Oberschenkel", ("Beine",)),
        ("Hintern", ("Po",)),
        ("bauch bauch", ("Bauch",)),
        ("keine ahnung", ()),
    ],
)
def test_detect_zones(text, expected):
    assert detect_zones(text) == expected
