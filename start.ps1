# =============================================================================
# PoolGuard — Start Script (Windows PowerShell)
# =============================================================================
# Opens two separate terminals: one for the backend, one for the frontend.
# =============================================================================
$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

# Validate .env exists
if (-not (Test-Path "$ROOT\backend\config\.env")) {
    Write-Error ".env not found at backend\config\.env. Run .\setup.ps1 first."
    exit 1
}

Write-Host "Starting PoolGuard backend  → http://localhost:8000" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& '$ROOT\.venv\Scripts\Activate.ps1'; Set-Location '$ROOT\backend'; uvicorn core.app:app --host 0.0.0.0 --port 8000 --reload"
)

Write-Host "Starting PoolGuard frontend → http://localhost:5173" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$ROOT\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Both servers are starting in separate windows." -ForegroundColor Green
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
