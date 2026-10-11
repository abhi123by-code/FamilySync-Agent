from __future__ import annotations

from core.models import Event, Task
from core.scheduler import detect_conflicts, get_events_for_date, member_available, validate_event


class ScheduleManager:
    def __init__(self, members, events):
        self.members = members
        self.events = events

    def get_events_for_date(self, target_date: str) -> list[Event]:
        return get_events_for_date(self.events, target_date)

    def detect_conflicts(self) -> list:
        return detect_conflicts(self.events)

    def get_member_availability(self, member_name: str, task: Task) -> bool:
        return member_available(member_name, self.events, task)

    def validate_event(self, event: Event) -> tuple[bool, str]:
        return validate_event(event, self.events)
