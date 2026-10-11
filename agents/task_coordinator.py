from __future__ import annotations

from core.models import CandidateResolution, Event, FamilyMember, Task
from core.resolver import resolve_task


class TaskCoordinator:
    def __init__(self, members: list[FamilyMember], events: list[Event]):
        self.members = members
        self.events = events

    def find_eligible_members(self, task: Task) -> list[CandidateResolution]:
        success, candidates, _ = resolve_task(task, self.members, self.events)
        if not success:
            return []
        return candidates

    def choose_best_member(self, task: Task) -> str:
        candidates = self.find_eligible_members(task)
        if not candidates:
            return "Unassigned"
        return candidates[0].member
