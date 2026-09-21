import httpx
import pytest

from app.ai_contract import ChatMessage
from app.openrouter import (
    MODEL,
    OpenRouterConfigurationError,
    OpenRouterRequestError,
    answer_board_question,
    answer_two_plus_two,
)


class FakeStream:
    """Stands in for the context manager returned by httpx.stream."""

    def __init__(self, status_code, **kwargs) -> None:
        self.response = httpx.Response(status_code, **kwargs)

    def __enter__(self) -> httpx.Response:
        return self.response

    def __exit__(self, *_args) -> bool:
        return False


def stub_completion(monkeypatch, content: str) -> dict:
    """Reply to every OpenRouter call with `content` and record the request sent."""
    request_data: dict = {}

    def mock_stream(_method, url, *, headers, json, timeout):
        request_data.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeStream(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": content}}]},
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("app.openrouter.httpx.stream", mock_stream)
    return request_data


def stub_failure(monkeypatch, error: Exception) -> None:
    """Make every OpenRouter call raise `error`."""

    def mock_stream(*_args, **_kwargs):
        raise error

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("app.openrouter.httpx.stream", mock_stream)


def test_answer_two_plus_two_uses_the_configured_model(monkeypatch) -> None:
    request_data = stub_completion(monkeypatch, "2 + 2 = 4")

    assert answer_two_plus_two() == "2 + 2 = 4"
    assert request_data["json"]["model"] == MODEL
    assert request_data["json"]["messages"] == [{"role": "user", "content": "What is 2+2?"}]
    assert request_data["headers"]["Authorization"] == "Bearer test-key"


def test_answer_two_plus_two_requires_an_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(OpenRouterConfigurationError, match="OPENROUTER_API_KEY"):
        answer_two_plus_two()


def test_answer_two_plus_two_wraps_upstream_failures(monkeypatch) -> None:
    stub_failure(monkeypatch, httpx.ConnectError("unavailable"))

    with pytest.raises(OpenRouterRequestError, match="valid response"):
        answer_two_plus_two()


def test_answer_board_question_sends_board_history_and_structured_schema(monkeypatch) -> None:
    request_data = stub_completion(
        monkeypatch, '{"version":"1","response":"Done.","operations":[]}'
    )
    board = {"columns": [], "cards": {}}
    history = [ChatMessage(role="user", content="Earlier question")]

    response = answer_board_question(board, history, "What should I do?")

    assert response.response == "Done."
    payload = request_data["json"]
    assert payload["model"] == MODEL
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert '"board": {"columns": [], "cards": {}}' in payload["messages"][1]["content"]
    assert '"conversation_history": [{"role": "user", "content": "Earlier question"}]' in payload["messages"][1]["content"]
    assert '"question": "What should I do?"' in payload["messages"][1]["content"]


def test_timeouts_get_a_distinct_message(monkeypatch) -> None:
    stub_failure(monkeypatch, httpx.ReadTimeout("slow"))

    with pytest.raises(OpenRouterRequestError, match="took too long"):
        answer_two_plus_two()


def test_a_response_that_never_finishes_hits_the_total_deadline(monkeypatch) -> None:
    class SlowStream:
        def __enter__(self):
            return httpx.Response(200, request=httpx.Request("POST", "https://x"), content=b"{}")

        def __exit__(self, *_args) -> bool:
            return False

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("app.openrouter.httpx.stream", lambda *_a, **_k: SlowStream())
    monkeypatch.setattr("app.openrouter.REQUEST_TIMEOUT_SECONDS", -1.0)

    with pytest.raises(OpenRouterRequestError, match="took too long"):
        answer_two_plus_two()
