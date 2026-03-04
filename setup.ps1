# =============================================================================
# PoolGuard — First-Time Setup Script (Windows PowerShell)
# =============================================================================
$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

Write-Host "==============================" -ForegroundColor Cyan
Write-Host "  PoolGuard - Setup" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

# ---------- Backend -----------------------------------------------------------
Write-Host "`n[1/4] Creating Python virtual environment..."
python -m venv "$ROOT\.venv"
& "$ROOT\.venv\Scripts\Activate.ps1"

Write-Host "[2/4] Installing backend dependencies..."
pip install --upgrade pip
pip install -r "$ROOT\backend\config\requirements.txt"

# ---------- Environment file --------------------------------------------------
Write-Host "[3/4] Checking .env file..."
$envFile    = "$ROOT\backend\config\.env"
$exampleFile = "$ROOT\backend\config\.env.example"

if (-not (Test-Path $envFile)) {
    Copy-Item $exampleFile $envFile
    Write-Host ""
    Write-Host "  *** IMPORTANT ***" -ForegroundColor Yellow
    Write-Host "  $envFile has been created from the template."
    Write-Host "  Edit it now and fill in ALL <CHANGE_ME> values before starting."
    Write-Host ""
} else {
    Write-Host "  .env already exists - skipping copy."
}

# ---------- Frontend ----------------------------------------------------------
Write-Host "[4/4] Installing frontend dependencies..."
Push-Location "$ROOT\frontend"
npm install
Pop-Location

Write-Host ""
Write-Host "==============================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "  Next: edit backend\config\.env, then run .\start.ps1" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Green
