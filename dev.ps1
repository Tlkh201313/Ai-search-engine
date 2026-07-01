# Lumen dev launcher — starts the FastAPI backend and the Next.js frontend together.
# Usage (from the repo root):  ./dev.ps1
#
# The backend reads its port from apps/api/.env (API_PORT, default 8001). Keep
# NEXT_PUBLIC_API_URL in apps/web/.env.local pointed at the same port.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$api = Join-Path $root 'apps\api'
$web = Join-Path $root 'apps\web'

# Prefer the backend virtualenv's Python; fall back to system python.
$py = Join-Path $api '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

# Prefer pnpm; fall back to npm.
$pm = if (Get-Command pnpm -ErrorAction SilentlyContinue) { 'pnpm' } else { 'npm' }

Write-Host 'Starting Lumen backend (apps/api)  -> new window' -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$api'; & '$py' -m app"

Write-Host 'Starting Lumen frontend (apps/web) -> new window' -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$web'; $pm run dev"

Write-Host ''
Write-Host 'Backend :  http://localhost:8001/health   (API_PORT in apps/api/.env)' -ForegroundColor Green
Write-Host 'Frontend:  http://localhost:3000' -ForegroundColor Green
Write-Host 'Two windows opened. Close each (or Ctrl+C) to stop the servers.'
