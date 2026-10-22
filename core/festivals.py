from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Festival:
    name: str
    message: str
    emoji: str


_ANNUAL_FESTIVALS = {
    (1, 1): Festival("New Year's Day", "Wishing your family a bright start to the year!", "🎉"),
    (1, 14): Festival("Makar Sankranti", "Celebrate the harvest and the brighter days ahead.", "🪁"),
    (1, 26): Festival("Republic Day (India)", "A day to celebrate India's unity and spirit.", "🇮🇳"),
    (2, 14): Festival("Valentine's Day", "Share a little extra love with the people close to you.", "💝"),
    (3, 8): Festival("International Women's Day", "Celebrating the strength and achievements of women.", "🌷"),
    (8, 15): Festival("Independence Day (India)", "Wishing you a proud and joyful Independence Day!", "🇮🇳"),
    (9, 5): Festival("Teachers' Day (India)", "Thank a teacher who has made a difference in your life.", "📚"),
    (10, 1): Festival("International Coffee Day", "Take a little coffee break and share a warm moment.", "☕"),
    (10, 2): Festival("Gandhi Jayanti (India)", "Remember the values of peace and kindness.", "🕊️"),
    (10, 11): Festival("International Day of the Girl Child", "Celebrating the rights, potential, and future of every girl.", "🌟"),
    (10, 31): Festival("Halloween", "Wishing your family a fun and delightfully spooky day!", "🎃"),
    (11, 14): Festival("Children's Day (India)", "Celebrate the curiosity and joy children bring to every day.", "🎈"),
    (12, 25): Festival("Christmas", "Wishing your family a warm and joyful Christmas!", "🎄"),
}

_MOVABLE_FESTIVALS = {
    2024: {
        (3, 25): Festival("Holi", "May your day be filled with colour, laughter, and togetherness.", "🎨"),
        (9, 7): Festival("Ganesh Chaturthi", "Wishing your family wisdom, joy, and new beginnings.", "🐘"),
        (11, 1): Festival("Diwali", "May the festival of lights bring warmth and happiness to your home.", "🪔"),
    },
    2025: {
        (3, 14): Festival("Holi", "May your day be filled with colour, laughter, and togetherness.", "🎨"),
        (8, 27): Festival("Ganesh Chaturthi", "Wishing your family wisdom, joy, and new beginnings.", "🐘"),
        (10, 2): Festival("Dussehra (Vijayadashami)", "Celebrate the victory of good over evil and the joy of new beginnings.", "🎉"),
        (10, 20): Festival("Diwali", "May the festival of lights bring warmth and happiness to your home.", "🪔"),
    },
    2026: {
        (3, 4): Festival("Holi", "May your day be filled with colour, laughter, and togetherness.", "🎨"),
        (9, 14): Festival("Ganesh Chaturthi", "Wishing your family wisdom, joy, and new beginnings.", "🐘"),
        (10, 20): Festival("Dussehra (Vijayadashami)", "Celebrate the victory of good over evil and the joy of new beginnings.", "🎉"),
        (11, 8): Festival("Diwali", "May the festival of lights bring warmth and happiness to your home.", "🪔"),
    },
    2027: {
        (3, 22): Festival("Holi", "May your day be filled with colour, laughter, and togetherness.", "🎨"),
        (9, 4): Festival("Ganesh Chaturthi", "Wishing your family wisdom, joy, and new beginnings.", "🐘"),
        (10, 10): Festival("Dussehra (Vijayadashami)", "Celebrate the victory of good over evil and the joy of new beginnings.", "🎉"),
        (10, 29): Festival("Diwali", "May the festival of lights bring warmth and happiness to your home.", "🪔"),
    },
    2028: {
        (3, 11): Festival("Holi", "May your day be filled with colour, laughter, and togetherness.", "🎨"),
        (8, 23): Festival("Ganesh Chaturthi", "Wishing your family wisdom, joy, and new beginnings.", "🐘"),
        (10, 5): Festival("Dussehra (Vijayadashami)", "Celebrate the victory of good over evil and the joy of new beginnings.", "🎉"),
        (10, 17): Festival("Diwali", "May the festival of lights bring warmth and happiness to your home.", "🪔"),
    },
    2029: {
        (3, 1): Festival("Holi", "May your day be filled with colour, laughter, and togetherness.", "🎨"),
        (9, 11): Festival("Ganesh Chaturthi", "Wishing your family wisdom, joy, and new beginnings.", "🐘"),
        (10, 13): Festival("Dussehra (Vijayadashami)", "Celebrate the victory of good over evil and the joy of new beginnings.", "🎉"),
        (11, 5): Festival("Diwali", "May the festival of lights bring warmth and happiness to your home.", "🪔"),
    },
    2030: {
        (3, 20): Festival("Holi", "May your day be filled with colour, laughter, and togetherness.", "🎨"),
        (9, 1): Festival("Ganesh Chaturthi", "Wishing your family wisdom, joy, and new beginnings.", "🐘"),
        (10, 2): Festival("Dussehra (Vijayadashami)", "Celebrate the victory of good over evil and the joy of new beginnings.", "🎉"),
        (10, 26): Festival("Diwali", "May the festival of lights bring warmth and happiness to your home.", "🪔"),
    },
}

_SPECIAL_DAY_FALLBACK = Festival(
    "Special Day",
    "Every day is a chance to celebrate love, gratitude, and togetherness.",
    "✨",
)

_INDIAN_FESTIVAL_KEYWORDS = (
    "india",
    "dussehra",
    "vijayadashami",
    "diwali",
    "holi",
    "ganesh",
    "makar",
    "republic",
    "independence",
    "teachers",
    "children",
    "gandhi",
    "navratri",
)


def _is_indian_festival(festival: Festival) -> bool:
    value = festival.name.lower()
    return any(keyword in value for keyword in _INDIAN_FESTIVAL_KEYWORDS)


def get_festival_for_date(day: date) -> Festival:
    """Return the most relevant Indian or international celebration for the given day."""
    matches: list[Festival] = []

    movable = _MOVABLE_FESTIVALS.get(day.year, {}).get((day.month, day.day))
    if movable:
        matches.append(movable)

    annual = _ANNUAL_FESTIVALS.get((day.month, day.day))
    if annual:
        matches.append(annual)

    if day.month == 7 and day.day == 30:
        matches.append(Festival("International Friendship Day", "Celebrate the friends who make life brighter.", "🫶"))
    if day.month == 8 and day.weekday() == 6 and 1 <= day.day <= 7:
        matches.append(Festival("Friendship Day", "Reach out to a friend and share a little happiness.", "🤝"))

    if not matches:
        return _SPECIAL_DAY_FALLBACK

    for festival in matches:
        if _is_indian_festival(festival):
            return festival

    return matches[0]
