import pytest

from app.ai_contract import StructuredOutputError, parse_ai_response


def test_parses_a_structured_chat_only_response() -> None:
    response = parse_ai_response(
        '{"version":"1","response":"I can help with that.","operations":[]}'
    )

    assert response.response == "I can help with that."
    assert response.operations == []


def test_rejects_an_invalid_structured_response() -> None:
    with pytest.raises(StructuredOutputError, match="invalid structured response"):
        parse_ai_response('{"response":"Missing required fields"}')
