#!/usr/bin/env bash
# =============================================================================
# PoolGuard — Start Script (Linux / macOS)
# =============================================================================
# Starts the FastAPI backend and the Vite dev server in parallel.
# For production, build the frontend first and serve via a reverse proxy.
# =============================================================================
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Activate venv
source "$ROOT_DIR/.venv/bin/activate"

# Validate .env exists
if [ ! -f "$ROOT_DIR/backend/config/.env" ]; then
    echo "[ERROR] backend/config/.env not found."
    echo "        Run ./setup.sh first, then fill in credentials."
    exit 1
fi

echo "Starting PoolGuard backend on http://localhost:8000 ..."
cd "$ROOT_DIR/backend"
uvicorn core.app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Starting PoolGuard frontend on http://localhost:5173 ..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo "  Press Ctrl+C to stop both."

# Wait and clean up on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
