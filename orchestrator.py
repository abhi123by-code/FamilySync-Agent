from __future__ import annotations

from agents.communication_agent import CommunicationAgent
from agents.schedule_manager import ScheduleManager
from agents.task_coordinator import TaskCoordinator
from core.models import CoordinationResult, Event, Task
from services.llm_service import LLMService


class Orchestrator:
    def __init__(self, members, events, tasks):
        self.members = members
        self.events = events
        self.tasks = tasks
        self.schedule_manager = ScheduleManager(members, events)
        self.task_coordinator = TaskCoordinator(members, events)
        self.communication_agent = CommunicationAgent()
        self.llm = LLMService()

    def coordinate_event(self, request: str, event: Event) -> CoordinationResult:
        decision_log: list[str] = []
        decision_log.append("Request received by orchestrator.")
        decision_log.append("Schedule manager checked current family commitments.")
        validation_ok, msg = self.schedule_manager.validate_event(event)
        if not validation_ok:
            return CoordinationResult(
                request=request,
                status="rejected",
                recommendation="No update applied.",
                explanation=msg,
                decision_log=decision_log + [f"Rejected: {msg}"],
            )
        decision_log.append("Relevant events retrieved and validity confirmed.")
        scheduled_conflicts = self.schedule_manager.detect_conflicts()
        decision_log.append(f"Detected {len(scheduled_conflicts)} conflict(s).")
        task = Task(
            id=f"task-for-{event.id}",
            title=event.title,
            owner=event.member,
            start=event.start,
            end=event.end,
            priority="medium",
            category=event.category,
            description=event.notes,
        )
        candidates = self.task_coordinator.find_eligible_members(task)
        recommendation = "No feasible assignment found."
        if candidates:
            recommendation = f"Recommended assignment: {candidates[0].member}."
            status = "resolved"
        else:
            status = "unresolved"
        explanation = self.communication_agent.explain_resolution(recommendation, status)
        decision_log.append("Candidate members were evaluated and ranked.")
        decision_log.append("Final coordination message prepared.")
        return CoordinationResult(
            request=request,
            detected_conflicts=scheduled_conflicts,
            candidate_members=[candidate.member for candidate in candidates],
            recommendation=recommendation,
            explanation=explanation,
            status=status,
            decision_log=decision_log,
        )

    def parse_natural_language(self, request: str) -> dict:
        return self.llm.parse_request(request)
