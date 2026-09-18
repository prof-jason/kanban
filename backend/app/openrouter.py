import json
import os

import httpx

from app.ai_contract import AiChatResponse, ChatMessage, parse_ai_response, response_schema

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


class OpenRouterConfigurationError(Exception):
    pass


class OpenRouterRequestError(Exception):
    pass


def answer_two_plus_two() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterConfigurationError("OPENROUTER_API_KEY is not configured.")

    try:
        response = httpx.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "What is 2+2?"}],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as error:
        raise OpenRouterRequestError("OpenRouter did not return a valid response.") from error

    if not isinstance(content, str) or not content.strip():
        raise OpenRouterRequestError("OpenRouter did not return a valid response.")
    return content


def answer_board_question(
    board: dict[str, object], history: list[ChatMessage], question: str
) -> AiChatResponse:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterConfigurationError("OPENROUTER_API_KEY is not configured.")

    try:
        response = httpx.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You manage a Kanban board. Return JSON matching the requested schema. Use an empty operations list when no board change is needed.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "board": board,
                                "conversation_history": [message.model_dump() for message in history],
                                "question": question,
                            }
                        ),
                    },
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "kanban_chat_response",
                        "strict": True,
                        "schema": response_schema(),
                    },
                },
            },
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as error:
        raise OpenRouterRequestError("OpenRouter did not return a valid response.") from error

    if not isinstance(content, str):
        raise OpenRouterRequestError("OpenRouter did not return a valid response.")
    return parse_ai_response(content)