from __future__ import annotations


class CommunicationAgent:
    @staticmethod
    def _describe_conflict(item) -> str:
        if isinstance(item, dict):
            member = item.get("member") or item.get("name") or "Unknown member"
            title = item.get("title") or item.get("summary") or item.get("event") or "an event"
            return f"{member} ({title})"

        member = getattr(item, "member", None) or getattr(item, "name", None) or "Unknown member"
        title = getattr(item, "title", None) or getattr(item, "summary", None) or getattr(item, "event", None) or "an event"
        return f"{member} ({title})"

    def explain_conflict(self, conflicts: list, request: str) -> str:
        if not conflicts:
            return "No conflicts found for the current schedule."

        conflict_names = [self._describe_conflict(item) for item in conflicts[:3]]
        if len(conflicts) > 3:
            conflict_names.append(f"and {len(conflicts) - 3} more")
        names = ", ".join(conflict_names)
        return f"The update for '{request}' conflicts with existing commitments for {names}."

    def explain_resolution(self, recommendation: str, status: str) -> str:
        normalized_status = (status or "").strip().lower()
        if normalized_status == "resolved":
            return f"Recommended action: {recommendation}. This keeps the family schedule valid and preserves the lowest-risk change."
        return f"No feasible assignment is available right now. The schedule remains unchanged until a valid alternative is accepted."
