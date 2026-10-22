from datetime import date, datetime

from core.festivals import get_festival_for_date

from app import get_dashboard_timestamp


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


def test_get_festival_for_dussehra_priority():
    festival = get_festival_for_date(date(2026, 10, 20))

    assert festival is not None
    assert festival.name == "Dussehra (Vijayadashami)"


def test_get_festival_returns_special_day_fallback_on_regular_day():
    festival = get_festival_for_date(date(2026, 6, 12))

    assert festival is not None
    assert festival.name == "Special Day"


def test_get_dashboard_timestamp_formats_live_time():
    today, clock = get_dashboard_timestamp(datetime(2026, 10, 20, 9, 6, 0))

    assert today == "Tuesday, 20 October 2026"
    assert clock == "09:06 AM"
