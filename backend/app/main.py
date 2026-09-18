import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.database import (
    create_card,
    delete_card,
    get_or_create_board,
    initialize_database,
    move_card,
    rename_column,
    update_card,
)

STATIC_DIRECTORY = Path(__file__).resolve().parent.parent / "static"
SESSION_SECRET = os.getenv("SESSION_SECRET", "local-development-session-secret")
MVP_USERNAME = "user"
MVP_PASSWORD = "password"


class LoginRequest(BaseModel):
    username: str
    password: str


class ColumnUpdate(BaseModel):
    title: str


class CardCreate(BaseModel):
    column_id: str
    title: str
    details: str = ""


class CardUpdate(BaseModel):
    title: str
    details: str


class CardMove(BaseModel):
    column_id: str
    position: int = Field(ge=0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Project Management MVP", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")


def get_authenticated_username(request: Request) -> str:
    username = request.session.get("username")
    if username != MVP_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    return username


@app.post("/api/auth/login", status_code=status.HTTP_204_NO_CONTENT)
def login(credentials: LoginRequest, request: Request) -> Response:
    if credentials.username != MVP_USERNAME or credentials.password != MVP_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

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
def get_board(request: Request) -> dict[str, object]:
    return get_or_create_board(get_authenticated_username(request))


@app.patch("/api/board/columns/{column_id}")
def update_column(
    column_id: str, change: ColumnUpdate, request: Request
) -> dict[str, object]:
    try:
        return rename_column(get_authenticated_username(request), column_id, change.title)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post("/api/board/cards", status_code=status.HTTP_201_CREATED)
def add_card(change: CardCreate, request: Request) -> dict[str, object]:
    try:
        return create_card(
            get_authenticated_username(request),
            change.column_id,
            change.title,
            change.details,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.patch("/api/board/cards/{card_id}")
def edit_card(
    card_id: str, change: CardUpdate, request: Request
) -> dict[str, object]:
    try:
        return update_card(
            get_authenticated_username(request), card_id, change.title, change.details
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post("/api/board/cards/{card_id}/move")
def move_board_card(
    card_id: str, change: CardMove, request: Request
) -> dict[str, object]:
    try:
        return move_card(
            get_authenticated_username(request), card_id, change.column_id, change.position
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.delete("/api/board/cards/{card_id}")
def remove_card(card_id: str, request: Request) -> dict[str, object]:
    try:
        return delete_card(get_authenticated_username(request), card_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@app.get("/api/example")
def get_example() -> dict[str, str]:
    return {"message": "Hello from the API"}


app.mount("/", StaticFiles(directory=STATIC_DIRECTORY, html=True), name="static")