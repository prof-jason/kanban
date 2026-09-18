# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Project management MVP: a Kanban board with an AI chat sidebar. Next.js frontend, FastAPI backend, SQLite, all packaged in one Docker container. Login is hardcoded (`user` / `password`) but the DB schema supports multiple users. One board per user. `AGENTS.md` files (root, `backend/`, `frontend/`, `scripts/`) hold detailed per-area guidance; `docs/PLAN.md` is the staged plan and should be reviewed before starting work; `docs/AI.md` and `docs/DATABASE.md` describe the AI contract and schema.

## Commands

- Run the app: `./scripts/start.sh` (Docker Compose build + detach; serves on http://localhost:8000). Stop: `./scripts/stop.sh`. PowerShell equivalents exist. Scripts only start/stop; no setup logic belongs there.
- Backend tests: `cd backend && uv run pytest` (single test: `uv run pytest tests/test_main.py::test_name`)
- Frontend (from `frontend/`): `npm run dev`, `npm run build`, `npm run lint`, `npm run test:unit` (Vitest; single file: `npx vitest run src/lib/kanban.test.ts`), `npm run test:e2e` (Playwright; starts or reuses the Compose service on port 8000), `npm run test:all`.

## Architecture

- The Dockerfile is multi-stage: Next.js is built and statically exported (`frontend/out`), then copied into the Python image as `static/`, which FastAPI serves at `/`. The frontend therefore has no Node server at runtime; it talks to `/api/*` same-origin.
- Backend (`backend/app/`): `main.py` (routes, kept small), `database.py` (all SQLite operations; DB at `/data/project_management.db` in the `kanban-data` volume, created at startup), `openrouter.py` (server-only OpenRouter client), `ai_contract.py` (versioned structured-output schema and validation).
- Auth is a signed cookie session (`itsdangerous`) via `/api/auth/login|session|logout`. All `/api/board` and `/api/ai` routes require it.
- Every board mutation endpoint returns the complete ordered board; the frontend treats API responses as the source of truth and keeps only presentational/request state locally.
- AI chat flow (`POST /api/ai/chat`): sends the current board plus the last 10 persisted messages (`chat_messages` table) to OpenRouter with a strict JSON schema; the backend parses the output and validates every referenced column/card/position against the current board before applying any operation (`rename_column`, `create_card`, `update_card`, `move_card`, `delete_card`). Invalid output means an error and no board change. The response includes the new board, which `ChatSidebar` hands to `KanbanBoard` for an immediate refresh.
- Frontend (`frontend/src/`): `AuthGate` -> `KanbanBoard` (+ `ChatSidebar`) -> `KanbanColumn`/`KanbanCard`; `@dnd-kit` for drag-and-drop; pure board helpers in `lib/kanban.ts`. Tests use `data-testid` selectors like `column-col-backlog` and `card-card-1`; preserve or deliberately update them.
- `OPENROUTER_API_KEY` comes from the root `.env` and is exposed to the backend container only. Model: `nvidia/nemotron-3-ultra-550b-a55b:free`.

## Conventions

- Keep it simple; do not over-engineer or add unrequested features. No emojis anywhere. Keep the README minimal.
- Find the root cause with evidence before fixing a bug; do not guess.
- Use project colors from `frontend/src/app/globals.css`: yellow `#ecad0a`, blue `#209dd7`, purple `#753991`, navy `#032147`, gray `#888888`.
