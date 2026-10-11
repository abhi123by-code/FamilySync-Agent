from core.models import Event, FamilyMember, Task
from core.scheduler import detect_conflicts, get_events_for_date, member_available, overlaps, validate_event


def test_event_overlap_detection():
    event_a = Event(id="a", title="Meeting", member="Abhi", start="2026-10-10T10:00:00", end="2026-10-10T11:00:00", category="school")
    event_b = Event(id="b", title="Call", member="Abhi", start="2026-10-10T10:30:00", end="2026-10-10T11:30:00", category="family")
    assert overlaps(event_a.start, event_a.end, event_b.start, event_b.end) is True
    assert len(detect_conflicts([event_a, event_b])) == 1


def test_adjacent_events_do_not_overlap():
    event_a = Event(id="a", title="First", member="Mom", start="2026-10-10T09:00:00", end="2026-10-10T10:00:00")
    event_b = Event(id="b", title="Second", member="Mom", start="2026-10-10T10:00:00", end="2026-10-10T11:00:00")
    assert overlaps(event_a.start, event_a.end, event_b.start, event_b.end) is False


def test_member_available_false_when_event_overlaps_task():
    task = Task(id="t1", title="Pickup Arjun", owner="Dad", start="2026-10-10T16:15:00", end="2026-10-10T17:00:00")
    event = Event(id="e1", title="Dentist", member="Dad", start="2026-10-10T16:00:00", end="2026-10-10T17:00:00")
    assert member_available("Dad", [event], task) is False


def test_invalid_interval_rejected():
    event = Event(id="e1", title="Broken", member="Abhi", start="2026-10-10T12:00:00", end="2026-10-10T11:00:00")
    valid, message = validate_event(event, [])
    assert valid is False
    assert "after start" in message


def test_get_events_for_date_filters_by_day():
    events = [
        Event(id="a", title="One", member="Abhi", start="2026-10-10T08:00:00", end="2026-10-10T09:00:00"),
        Event(id="b", title="Two", member="Mom", start="2026-10-11T08:00:00", end="2026-10-11T09:00:00"),
    ]
    result = get_events_for_date(events, "2026-10-10")
    assert len(result) == 1
