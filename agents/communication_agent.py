from __future__ import annotations


class CommunicationAgent:
    def explain_conflict(self, conflicts: list, request: str) -> str:
        if not conflicts:
            return "No conflicts found for the current schedule."
        names = ", ".join(f"{item.member} ({item.title})" for item in conflicts[:3])
        return f"The update for '{request}' conflicts with existing commitments for {names}."

    def explain_resolution(self, recommendation: str, status: str) -> str:
        if status == "resolved":
            return f"Recommended action: {recommendation}. This keeps the family schedule valid and preserves the lowest-risk change."
        return f"No feasible assignment is available right now. The schedule remains unchanged until a valid alternative is accepted."
