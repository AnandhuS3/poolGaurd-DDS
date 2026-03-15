#!/bin/bash
# start_prod.sh - Production start script for Backend

export PYTHONPATH=/app
export HOST=0.0.0.0
export PORT=8000

# Apply pending migrations here if exist
# e.g., python database/update_schema.py

# Start uvicorn
exec uvicorn core.app:app --host $HOST --port $PORT --workers 4
