from types import SimpleNamespace

import pytest

from services.llm_service import LLMService


def test_chat_response_uses_gemini_with_context_and_history(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create_completion)
            )

        @staticmethod
        def create_completion(**kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="Dad has pickup at 4:15 PM.")
                    )
                ]
            )

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    service = LLMService(gemini_api_key="test-key")

    answer = service.chat_response(
        "When is pickup?",
        '{"tasks": ["Pickup Arjun"]}',
        [{"role": "user", "content": "Check today's schedule."}],
    )

    assert answer == "Dad has pickup at 4:15 PM."
    assert captured["client"]["base_url"].startswith(
        "https://generativelanguage.googleapis.com/"
    )
    assert captured["request"]["model"] == "gemini-3.8-flash"
    assert captured["request"]["messages"][1] == {
        "role": "user",
        "content": "Check today's schedule.",
    }
    assert captured["request"]["messages"][-1] == {
        "role": "user",
        "content": "When is pickup?",
    }


def test_chat_response_requires_a_configured_provider():
    service = LLMService(api_key="", gemini_api_key="")

    with pytest.raises(ValueError, match="No Gemini or OpenAI API key"):
        service.chat_response("Hello", "{}")