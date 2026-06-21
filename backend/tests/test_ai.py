from __future__ import annotations
import httpx
from app import ai

def test_chat_completion_returns_fallback_when_no_keys(monkeypatch):
    """Verify Groq chat falls back immediately when no API keys are configured."""
    monkeypatch.setattr(ai, "GROQ_API_KEY", "")
    monkeypatch.setattr(ai, "GROQ_API_KEY_FALLBACK", "")

    result = ai._chat_completion(
        messages=[{"role": "user", "content": "hello"}],
        fallback="fallback text",
        temperature=0.1,
        max_tokens=20,
        response_format=None,
        label="unit-test",
    )

    assert result == "fallback text"

def test_chat_completion_tries_fallback_key_after_http_error(monkeypatch):
    """Verify a failed primary Groq key does not prevent trying the fallback key."""
    monkeypatch.setattr(ai, "GROQ_API_KEY", "primary-key")
    monkeypatch.setattr(ai, "GROQ_API_KEY_FALLBACK", "fallback-key")

    class FakeResponse:
        def __init__(self, content: str | None = None, fail: bool = False):
            self._content = content
            self._fail = fail
            self.text = "rate limited"
            self.status_code = 429

        def raise_for_status(self) -> None:
            if self._fail:
                request = httpx.Request("POST", ai.GROQ_ENDPOINT)
                response = httpx.Response(429, request=request, text=self.text)
                raise httpx.HTTPStatusError("rate limited", request=request, response=response)

        def json(self) -> dict:
            return {"choices": [{"message": {"content": self._content}}]}

    class FakeClient:
        calls: list[str] = []

        def __init__(self, timeout: int):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def post(self, url: str, headers: dict, json: dict) -> FakeResponse:
            self.calls.append(headers["Authorization"])
            if len(self.calls) == 1:
                return FakeResponse(fail=True)
            return FakeResponse(content="successful response")

    monkeypatch.setattr(ai.httpx, "Client", FakeClient)

    result = ai._chat_completion(
        messages=[{"role": "user", "content": "hello"}],
        fallback="fallback text",
        temperature=0.1,
        max_tokens=20,
        response_format={"type": "json_object"},
        label="unit-test",
    )

    assert result == "successful response"
    assert FakeClient.calls == ["Bearer primary-key", "Bearer fallback-key"]

def test_load_json_object_extracts_fenced_json():
    """Verify fenced JSON responses are parsed into dictionaries."""
    result = ai._load_json_object('```json\n{"status": "ok"}\n```')

    assert result == {"status": "ok"}
