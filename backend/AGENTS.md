# Backend

This directory contains the FastAPI backend. It serves the statically exported frontend at `/`, exposes `GET /api/example` for a container smoke test, and owns MVP authentication.

- Dependencies and test configuration are in `pyproject.toml`; `uv.lock` is committed for reproducible installs.
- Application code is in `app/`; the ASGI entry point is `app.main:app`.
- Static files served by FastAPI are in `static/`.
- API tests live in `tests/` and run with `uv run pytest`.
- SQLite operations are in `app/database.py`. The database initializes at startup and is stored at `/data/project_management.db` in the `kanban-data` Compose volume.
- The application is built from the repository-root Dockerfile and exposed on port 8000 through `compose.yaml`.
- `POST /api/auth/login`, `GET /api/auth/session`, and `POST /api/auth/logout` implement the signed cookie session for the fixed MVP credentials.
- Authenticated board routes under `/api/board` return the complete ordered board after every mutation.
- `app/openrouter.py` provides the server-only OpenRouter client using `OPENROUTER_API_KEY` and `nvidia/nemotron-3-ultra-550b-a55b:free`. `POST /api/ai/connectivity` is an authenticated, opt-in `2+2` check.
- `POST /api/ai/chat` supplies the current board and the last 10 saved messages to OpenRouter. It accepts only the versioned structured output in `app/ai_contract.py` and returns assistant text plus the resulting board.

Keep route handlers small. Add persistence and AI integrations only in their respective approved plan stages.