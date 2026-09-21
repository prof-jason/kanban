import os
import secrets
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from app.ai_contract import AiChatResponse, ChatMessage, StructuredOutputError, operation_to_dict
from app.database import (
    apply_ai_operations,
    create_card,
    delete_card,
    get_chat_history,
    get_or_create_board,
    initialize_database,
    move_card,
    record_chat_messages,
    rename_column,
    update_card,
)
from app.openrouter import (
    OpenRouterConfigurationError,
    OpenRouterRequestError,
    answer_board_question,
    answer_two_plus_two,
)

STATIC_DIRECTORY = Path(__file__).resolve().parent.parent / "static"
# Without SESSION_SECRET a random key is used, so sessions end when the server restarts.
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_urlsafe(32)
SESSION_HTTPS_ONLY = os.getenv("SESSION_HTTPS_ONLY") == "1"
MVP_USERNAME = os.getenv("MVP_USERNAME", "user")
MVP_PASSWORD = os.getenv("MVP_PASSWORD", "password")
TITLE_MAX_LENGTH = 200
DETAILS_MAX_LENGTH = 4000


class LoginRequest(BaseModel):
    username: str
    password: str


class ColumnUpdate(BaseModel):
    title: str = Field(max_length=TITLE_MAX_LENGTH)


class CardCreate(BaseModel):
    column_id: str
    title: str = Field(max_length=TITLE_MAX_LENGTH)
    details: str = Field(default="", max_length=DETAILS_MAX_LENGTH)


class CardUpdate(BaseModel):
    title: str = Field(max_length=TITLE_MAX_LENGTH)
    details: str = Field(max_length=DETAILS_MAX_LENGTH)


class CardMove(BaseModel):
    column_id: str
    position: int = Field(ge=0)


class AiChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Project Management MVP", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=SESSION_HTTPS_ONLY,
)


def get_authenticated_username(request: Request) -> str:
    username = request.session.get("username")
    if username != MVP_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    return username


AuthenticatedUsername = Annotated[str, Depends(get_authenticated_username)]


@contextmanager
def board_errors() -> Iterator[None]:
    """Translate database lookup and validation failures into HTTP responses."""
    try:
        yield
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


def _matches(supplied: str, expected: str) -> bool:
    return secrets.compare_digest(supplied.encode(), expected.encode())


@app.post("/api/auth/login", status_code=status.HTTP_204_NO_CONTENT)
def login(credentials: LoginRequest, request: Request) -> Response:
    if not (
        _matches(credentials.username, MVP_USERNAME)
        and _matches(credentials.password, MVP_PASSWORD)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    get_or_create_board(MVP_USERNAME)
    request.session["username"] = MVP_USERNAME
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/auth/session")
def get_session(request: Request) -> dict[str, str | bool]:
    username = request.session.get("username")
    return {"authenticated": username == MVP_USERNAME, "username": username or ""}


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/board")
def get_board(username: AuthenticatedUsername) -> dict[str, object]:
    return get_or_create_board(username)


@app.patch("/api/board/columns/{column_id}")
def update_column(
    column_id: str, change: ColumnUpdate, username: AuthenticatedUsername
) -> dict[str, object]:
    with board_errors():
        return rename_column(username, column_id, change.title)


@app.post("/api/board/cards", status_code=status.HTTP_201_CREATED)
def add_card(change: CardCreate, username: AuthenticatedUsername) -> dict[str, object]:
    with board_errors():
        return create_card(username, change.column_id, change.title, change.details)


@app.patch("/api/board/cards/{card_id}")
def edit_card(
    card_id: str, change: CardUpdate, username: AuthenticatedUsername
) -> dict[str, object]:
    with board_errors():
        return update_card(username, card_id, change.title, change.details)


@app.post("/api/board/cards/{card_id}/move")
def move_board_card(
    card_id: str, change: CardMove, username: AuthenticatedUsername
) -> dict[str, object]:
    with board_errors():
        return move_card(username, card_id, change.column_id, change.position)


@app.delete("/api/board/cards/{card_id}")
def remove_card(card_id: str, username: AuthenticatedUsername) -> dict[str, object]:
    with board_errors():
        return delete_card(username, card_id)


@app.post("/api/ai/connectivity")
def check_ai_connectivity(_: AuthenticatedUsername) -> dict[str, str]:
    try:
        return {"response": answer_two_plus_two()}
    except OpenRouterConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    except OpenRouterRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@app.post("/api/ai/chat")
def chat_with_ai(change: AiChatRequest, username: AuthenticatedUsername) -> dict[str, object]:
    board = get_or_create_board(username)
    history = [ChatMessage.model_validate(message) for message in get_chat_history(username)]
    try:
        ai_response = answer_board_question(board, history, change.question)
        board = apply_ai_operations(
            username, [operation_to_dict(operation) for operation in ai_response.operations]
        )
    except (OpenRouterRequestError, StructuredOutputError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except OpenRouterConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error

    record_chat_messages(
        username,
        [
            {"role": "user", "content": change.question},
            {"role": "assistant", "content": ai_response.response},
        ],
    )
    return {"response": ai_response.response, "board": board}


@app.get("/api/ai/history")
def get_ai_history(username: AuthenticatedUsername) -> dict[str, list[dict[str, str]]]:
    return {"messages": get_chat_history(username)}


@app.get("/api/example")
def get_example() -> dict[str, str]:
    return {"message": "Hello from the API"}


app.mount("/", StaticFiles(directory=STATIC_DIRECTORY, html=True), name="static")
