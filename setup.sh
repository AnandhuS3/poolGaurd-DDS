#!/usr/bin/env bash
# =============================================================================
# PoolGuard — First-Time Setup Script (Linux / macOS)
# =============================================================================
set -e

echo "=============================="
echo "  PoolGuard — Setup"
echo "=============================="

# ---------- Backend -----------------------------------------------------------
echo ""
echo "[1/4] Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "[2/4] Installing backend dependencies..."
pip install --upgrade pip
pip install -r backend/config/requirements.txt

# ---------- Environment file --------------------------------------------------
echo "[3/4] Checking .env file..."
ENV_FILE="backend/config/.env"
EXAMPLE_FILE="backend/config/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    cp "$EXAMPLE_FILE" "$ENV_FILE"
    echo ""
    echo "  *** IMPORTANT ***"
    echo "  $ENV_FILE has been created from the template."
    echo "  Edit it now and fill in ALL <CHANGE_ME> values before starting."
    echo ""
else
    echo "  .env already exists — skipping copy."
fi

# ---------- Frontend ----------------------------------------------------------
echo "[4/4] Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "=============================="
echo "  Setup complete!"
echo "  Next: edit backend/config/.env, then run ./start.sh"
echo "=============================="
