import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

STATIC_DIRECTORY = Path(__file__).resolve().parent.parent / "static"
SESSION_SECRET = os.getenv("SESSION_SECRET", "local-development-session-secret")
MVP_USERNAME = "user"
MVP_PASSWORD = "password"


class LoginRequest(BaseModel):
    username: str
    password: str

app = FastAPI(title="Project Management MVP")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")


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


@app.get("/api/example")
def get_example() -> dict[str, str]:
    return {"message": "Hello from the API"}


app.mount("/", StaticFiles(directory=STATIC_DIRECTORY, html=True), name="static")