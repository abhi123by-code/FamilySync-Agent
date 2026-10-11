from core.models import Event, FamilyMember, Task
from core.resolver import resolve_task


def build_members():
    return [
        FamilyMember(name="Abhi", preferences={"pickup": 0.7, "family": 0.7}),
        FamilyMember(name="Mom", preferences={"pickup": 0.9, "medical": 0.9}),
        FamilyMember(name="Dad", preferences={"pickup": 0.9, "errand": 0.8}),
        FamilyMember(name="Arjun", preferences={"pickup": 0.8}),
    ]


def test_resolve_task_with_valid_candidate():
    members = build_members()
    task = Task(id="pickup", title="Pickup Arjun", owner="Dad", start="2026-10-10T16:15:00", end="2026-10-10T17:00:00", category="pickup")
    events = [
        Event(id="e1", title="Dentist appointment", member="Mom", start="2026-10-10T15:00:00", end="2026-10-10T16:00:00"),
        Event(id="e2", title="College presentation", member="Abhi", start="2026-10-10T14:00:00", end="2026-10-10T16:00:00"),
    ]
    success, candidates, message = resolve_task(task, members, events)
    assert success is True
    assert candidates[0].member == "Dad"
    assert "Recommended assignment" in message


def test_resolve_task_no_candidate_when_everyone_busy():
    members = build_members()
    task = Task(id="pickup", title="Pickup Arjun", owner="Dad", start="2026-10-10T16:15:00", end="2026-10-10T17:00:00", category="pickup")
    events = [
        Event(id="e1", title="Dentist", member="Mom", start="2026-10-10T16:00:00", end="2026-10-10T17:00:00"),
        Event(id="e2", title="Meeting", member="Dad", start="2026-10-10T16:15:00", end="2026-10-10T17:00:00"),
        Event(id="e3", title="Interview", member="Abhi", start="2026-10-10T16:00:00", end="2026-10-10T17:15:00"),
        Event(id="e4", title="Club", member="Arjun", start="2026-10-10T16:30:00", end="2026-10-10T17:30:00"),
    ]
    success, candidates, message = resolve_task(task, members, events)
    assert success is False
    assert candidates == []
    assert "No feasible candidate" in message
