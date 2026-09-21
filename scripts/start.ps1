$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $ProjectRoot
docker compose up --build --detach
