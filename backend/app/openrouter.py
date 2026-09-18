import json
import os
import time

import httpx

from app.ai_contract import AiChatResponse, ChatMessage, parse_ai_response, response_schema

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
REQUEST_TIMEOUT_SECONDS = 90.0


class OpenRouterConfigurationError(Exception):
    pass


class OpenRouterRequestError(Exception):
    pass


def _read_completion(api_key: str, payload: dict[str, object]) -> str:
    # httpx timeouts apply per read, so a provider that keeps the connection alive
    # would never time out. Enforce a total deadline as well.
    deadline = time.monotonic() + REQUEST_TIMEOUT_SECONDS
    body = bytearray()
    with httpx.stream(
        "POST",
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            if time.monotonic() > deadline:
                raise httpx.ReadTimeout("Total request time exceeded.")
            body.extend(chunk)
    return json.loads(body)["choices"][0]["message"]["content"]


def _complete(payload: dict[str, object]) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterConfigurationError("OPENROUTER_API_KEY is not configured.")

    try:
        content = _read_completion(api_key, {"model": MODEL, **payload})
    except httpx.TimeoutException as error:
        raise OpenRouterRequestError("OpenRouter took too long to respond. Please try again.") from error
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
        raise OpenRouterRequestError("OpenRouter did not return a valid response.") from error

    if not isinstance(content, str) or not content.strip():
        raise OpenRouterRequestError("OpenRouter did not return a valid response.")
    return content


def answer_two_plus_two() -> str:
    return _complete({"messages": [{"role": "user", "content": "What is 2+2?"}]})


def answer_board_question(
    board: dict[str, object], history: list[ChatMessage], question: str
) -> AiChatResponse:
    content = _complete(
        {
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
        }
    )
    return parse_ai_response(content)
