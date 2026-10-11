from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class LLMService:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def parse_request(self, request: str) -> dict:
        if not self.api_key:
            return {
                "source": "fallback",
                "title": "Family coordination request",
                "member": "Abhi",
                "task_type": "family",
                "date": "2026-10-10",
                "start": "2026-10-10T17:00:00",
                "end": "2026-10-10T18:00:00",
                "summary": "Demo fallback: request parsed using deterministic local logic because no live LLM API key is configured.",
            }

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "user", "content": f"Extract a simple structured JSON for this family request: {request}. Return keys title, member, task_type, date, start, end, summary."}
                ],
            )
            content = response.output_text.strip()
            import json

            return json.loads(content)
        except Exception:
            return {
                "source": "fallback",
                "title": "Family coordination request",
                "member": "Abhi",
                "task_type": "family",
                "date": "2026-10-10",
                "start": "2026-10-10T17:00:00",
                "end": "2026-10-10T18:00:00",
                "summary": "The LLM call failed, so the demo fallback returned a structured request for local testing.",
            }
