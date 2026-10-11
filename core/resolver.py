from __future__ import annotations

from core.models import CandidateResolution, Event, FamilyMember, Task
from core.scheduler import member_available


def evaluate_candidates(task: Task, members: list[FamilyMember], events: list[Event]) -> list[CandidateResolution]:
    candidates: list[CandidateResolution] = []
    for member in members:
        if not member_available(member.name, events, task):
            continue

        score = 18.0 if member.name == task.owner else 5.0
        score += 10.0
        score += member.preferences.get(task.category, 0.0) * 10.0
        score += member.preferences.get(task.title.lower(), 0.0) * 6.0

        candidates.append(
            CandidateResolution(
                member=member.name,
                score=round(score, 2),
                reason=f"{member.name} has available time and matches the task pattern.",
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates


def resolve_task(task: Task, members: list[FamilyMember], events: list[Event]) -> tuple[bool, list[CandidateResolution], str]:
    candidates = evaluate_candidates(task, members, events)
    if not candidates:
        return False, [], "No feasible candidate is available at the required time."
    best = candidates[0]
    return True, candidates, f"Recommended assignment: {best.member}."
