from __future__ import annotations

from datetime import datetime

from core.models import Conflict, Event, Task


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def validate_interval(start: str, end: str) -> bool:
    try:
        start_dt = parse_iso(start)
        end_dt = parse_iso(end)
        return end_dt > start_dt
    except ValueError:
        return False


def overlaps(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    if not validate_interval(start_a, end_a) or not validate_interval(start_b, end_b):
        return False
    a_start = parse_iso(start_a)
    a_end = parse_iso(end_a)
    b_start = parse_iso(start_b)
    b_end = parse_iso(end_b)
    return a_start < b_end and b_start < a_end


def get_events_for_date(events: list[Event], target_date: str) -> list[Event]:
    return [event for event in events if event.start.startswith(target_date)]


def detect_conflicts(events: list[Event]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    for i, event in enumerate(events):
        for other in events[i + 1 :]:
            if event.member == other.member and overlaps(event.start, event.end, other.start, other.end):
                conflicts.append(
                    Conflict(
                        event_id=event.id,
                        title=event.title,
                        member=event.member,
                        other_event_id=other.id,
                        other_title=other.title,
                        start=min(event.start, other.start),
                        end=max(event.end, other.end),
                        description=f"{event.member} has overlapping events: {event.title} and {other.title}.",
                    )
                )
    return conflicts


def member_available(member_name: str, events: list[Event], task: Task) -> bool:
    for event in events:
        if event.member == member_name and overlaps(event.start, event.end, task.start, task.end):
            return False
    return True


def get_member_availability(member_name: str, events: list[Event], start: str, end: str) -> bool:
    for event in events:
        if event.member == member_name and overlaps(event.start, event.end, start, end):
            return False
    return True


def validate_event(event: Event, existing_events: list[Event]) -> tuple[bool, str]:
    if not validate_interval(event.start, event.end):
        return False, "Event end time must be after start time."
    for other in existing_events:
        if other.id == event.id:
            continue
        if other.member == event.member and overlaps(event.start, event.end, other.start, other.end):
            return False, f"{event.member} already has a conflicting event: {other.title}."
    return True, "Valid"
