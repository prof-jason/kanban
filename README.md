# Project Management MVP

Local Docker application for a persistent Kanban board with an AI project assistant.

## Run Locally

Start the container:

```sh
./scripts/start.sh
```

On Windows PowerShell, run:

```powershell
.\scripts\start.ps1
```

Open `http://localhost:8000` and sign in with:

- Username: `user`
- Password: `password`

The signed cookie session persists across browser refreshes. Use **Log out** to end it.

## Features

- Five fixed Kanban columns, with editable names.
- Create, edit, delete, reorder, and drag cards between columns.
- SQLite-backed board persistence in the Docker `kanban-data` volume.
- AI chat sidebar with persisted conversation history and automatic board updates from validated AI operations.
- OpenRouter integration using `nvidia/nemotron-3-ultra-550b-a55b:free`.

The root `.env` supplies `OPENROUTER_API_KEY` to the backend container only. Optional `.env` settings: `SESSION_SECRET` (random per start if unset, so sessions end on restart), `SESSION_HTTPS_ONLY=1`, `MVP_USERNAME` and `MVP_PASSWORD` (default `user` / `password`). `POST /api/ai/connectivity` is an authenticated, opt-in `2+2` connectivity check.

Stop the container:

```sh
./scripts/stop.sh
```

On Windows PowerShell, run:

```powershell
.\scripts\stop.ps1
```

## Tests

```sh
cd backend && uv run pytest
cd frontend && npm run test:all
```