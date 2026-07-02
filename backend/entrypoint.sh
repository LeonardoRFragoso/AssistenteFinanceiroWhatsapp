#!/bin/bash
set -e

# If a command is provided, exec it (allows docker-compose command override)
if [ $# -gt 0 ]; then
    exec "$@"
fi

# Use PORT from environment or default to 8000
PORT=${PORT:-8000}

# Start uvicorn with the correct port
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
