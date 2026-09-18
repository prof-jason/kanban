import httpx
import pytest

from app.openrouter import (
    MODEL,
    OpenRouterConfigurationError,
    OpenRouterRequestError,
    answer_two_plus_two,
)


def test_answer_two_plus_two_uses_the_configured_model(monkeypatch) -> None:
    request_data = {}

    def mock_post(url, *, headers, json, timeout):
        request_data.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": "2 + 2 = 4"}}]},
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("app.openrouter.httpx.post", mock_post)

    assert answer_two_plus_two() == "2 + 2 = 4"
    assert request_data["json"]["model"] == MODEL
    assert request_data["json"]["messages"] == [{"role": "user", "content": "What is 2+2?"}]
    assert request_data["headers"]["Authorization"] == "Bearer test-key"


def test_answer_two_plus_two_requires_an_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(OpenRouterConfigurationError, match="OPENROUTER_API_KEY"):
        answer_two_plus_two()


def test_answer_two_plus_two_wraps_upstream_failures(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def mock_post(*_args, **_kwargs):
        raise httpx.ConnectError("unavailable")

    monkeypatch.setattr("app.openrouter.httpx.post", mock_post)

    with pytest.raises(OpenRouterRequestError, match="valid response"):
        answer_two_plus_two()