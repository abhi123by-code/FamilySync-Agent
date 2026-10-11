from datetime import date

from core.festivals import get_festival_for_date


def test_get_festival_for_movable_festival_date():
    festival = get_festival_for_date(date(2026, 11, 8))

    assert festival is not None
    assert festival.name == "Diwali"
    assert festival.emoji == "🪔"


def test_get_festival_for_annual_international_observance():
    festival = get_festival_for_date(date(2026, 10, 1))

    assert festival is not None
    assert festival.name == "International Coffee Day"


def test_get_festival_for_indian_friendship_day():
    festival = get_festival_for_date(date(2026, 8, 2))

    assert festival is not None
    assert festival.name == "Friendship Day"


def test_get_festival_returns_none_on_regular_day():
    assert get_festival_for_date(date(2026, 6, 12)) is None
