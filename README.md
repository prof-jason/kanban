# Project Management MVP

Start the local container:

```sh
./scripts/start.sh
```

On Windows PowerShell, run:

```powershell
.\scripts\start.ps1
```

Open `http://localhost:8000` to use the Kanban board. Sign in with username `user` and password `password`. The backend example endpoint remains available at `/api/example`.

The root `.env` supplies `OPENROUTER_API_KEY` to the backend container only. An authenticated `POST /api/ai/connectivity` performs an opt-in `2+2` connectivity check.

Stop the container:

```sh
./scripts/stop.sh
```