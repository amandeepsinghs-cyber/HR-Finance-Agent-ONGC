#!/usr/bin/env bash
set -euo pipefail

# ---
# Cloud Run Deployment Flags (P3.2 / SPEC-03):
# Requires: --no-cpu-throttling --min-instances=1 --session-affinity --timeout=300
# ---

export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-ongc-hr-finance-agent}"
export TARGET_PROJECT="${TARGET_PROJECT:-ongc-hr-finance-agent}"
export GOOGLE_GENAI_USE_VERTEXAI="TRUE"
# B2: QuerySpec planner on by default (gate: root 87.5%, follow-ups 90%; D-31). Set YUKTI_PLANNER=0 to roll back.
export YUKTI_PLANNER="${YUKTI_PLANNER:-1}"
export YUKTI_BACKEND_URL="http://127.0.0.1:8095"
export PORT="${PORT:-8080}"
export HOST="0.0.0.0"

echo "[yukti-cloudrun] Starting FastAPI + ADK + Gemini Live backend on 127.0.0.1:8095..."
cd /app/yukti/backend
/app/yukti/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8095 &
BACKEND_PID=$!

# Wait for backend health
# 60 s: ADK / Vertex imports can be slow on a throttled cold start; stop early if the process died
for i in $(seq 1 60); do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "[yukti-cloudrun] Backend process exited during startup" >&2
    exit 1
  fi
  if curl -sf http://127.0.0.1:8095/health >/dev/null 2>&1; then
    echo "[yukti-cloudrun] Backend healthy on :8095"
    break
  fi
  sleep 1
done
if ! curl -sf http://127.0.0.1:8095/health >/dev/null 2>&1; then
  echo "[yukti-cloudrun] Backend did not become healthy within 60 s" >&2
  exit 1
fi

echo "[yukti-cloudrun] Starting Next.js + WebSocket single-origin server on 0.0.0.0:${PORT}..."
cd /app/yukti/frontend
env NODE_ENV=production PORT="${PORT}" HOST="0.0.0.0" YUKTI_BACKEND_URL="http://127.0.0.1:8095" node server.js &
FRONTEND_PID=$!
# Supervise both: if either exits, stop the container so Cloud Run restarts it (no endless 502s)
# bash is PID 1 now: forward Cloud Run's SIGTERM to both children for a clean, fast shutdown
trap 'kill -TERM "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null; wait; exit 0' TERM INT
wait -n "$BACKEND_PID" "$FRONTEND_PID" || true
echo "[yukti-cloudrun] A process exited; shutting down" >&2
kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
exit 1
