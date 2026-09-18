# Container Scripts

This directory contains lifecycle scripts for the local Docker Compose service.

- `start.sh` and `stop.sh` support macOS and Linux.
- `start.ps1` and `stop.ps1` support Windows PowerShell.
- Scripts resolve the repository root relative to their own location before running `docker compose`.

Keep these scripts limited to starting and stopping the local service. Do not place application setup or data migration logic here.