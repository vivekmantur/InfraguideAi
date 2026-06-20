#!/usr/bin/env bash
set -euo pipefail

export MCP_SERVER_URL="${MCP_SERVER_URL:-http://127.0.0.1:8000/mcp}"
export MCP_BRIDGE_URL="${MCP_BRIDGE_URL:-http://127.0.0.1:8001}"
export REDIS_URL="${REDIS_URL:-redis://host.docker.internal:6379/0}"

cd /app/cloud-intelligence-mcp
python app.py &
MCP_PID=$!

uvicorn bridge_api:app --host 0.0.0.0 --port 8001 &
BRIDGE_PID=$!

cd /app/backend
uvicorn app.main:app --host 0.0.0.0 --port 9000 &
BACKEND_PID=$!

cd /app
python docker/frontend_server.py &
FRONTEND_PID=$!

trap 'kill "$MCP_PID" "$BRIDGE_PID" "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true' INT TERM

wait -n "$MCP_PID" "$BRIDGE_PID" "$BACKEND_PID" "$FRONTEND_PID"
EXIT_CODE=$?

kill "$MCP_PID" "$BRIDGE_PID" "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
exit "$EXIT_CODE"
