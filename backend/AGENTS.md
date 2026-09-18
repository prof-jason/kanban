# Backend

This directory contains the FastAPI backend. It serves the statically exported frontend at `/`, exposes `GET /api/example` for a container smoke test, and owns MVP authentication.

- Dependencies and test configuration are in `pyproject.toml`; `uv.lock` is committed for reproducible installs.
- Application code is in `app/`; the ASGI entry point is `app.main:app`.
- Static files served by FastAPI are in `static/`.
- API tests live in `tests/` and run with `uv run pytest`.
- The application is built from the repository-root Dockerfile and exposed on port 8000 through `compose.yaml`.
- `POST /api/auth/login`, `GET /api/auth/session`, and `POST /api/auth/logout` implement the signed cookie session for the fixed MVP credentials.

Keep route handlers small. Add persistence and AI integrations only in their respective approved plan stages.