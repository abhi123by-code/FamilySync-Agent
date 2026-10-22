from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class LLMService:
    def __init__(
        self,
        api_key: str | None = None,
        gemini_api_key: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    def chat_response(
        self,
        message: str,
        family_context: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        from openai import OpenAI

        if self.gemini_api_key:
            client = OpenAI(
                api_key=self.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                timeout=30.0,
                max_retries=1,
            )
            model = self.gemini_model
        elif self.api_key:
            client = OpenAI(api_key=self.api_key, timeout=30.0, max_retries=1)
            model = self.model
        else:
            raise ValueError("No Gemini or OpenAI API key is configured.")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are FamilySync AI, a helpful family-planning assistant. "
                    "Answer the user's actual question directly, including general questions. "
                    "Use the family context when relevant, and never invent calendar events, "
                    "task status, or actions. If the saved data does not answer a question, "
                    "say what is missing and ask one concise follow-up. Keep replies clear "
                    "and conversational.\n\n"
                    f"Current family context (JSON): {family_context}"
                ),
            },
            *(history or []),
            {"role": "user", "content": message},
        ]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
        )
        answer = response.choices[0].message.content
        if not answer or not answer.strip():
            raise RuntimeError("The AI provider returned an empty response.")
        return answer.strip()

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
