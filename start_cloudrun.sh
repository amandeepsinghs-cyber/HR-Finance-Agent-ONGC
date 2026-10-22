#!/usr/bin/env bash
set -euo pipefail

export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-ongc-hr-finance-agent}"
export TARGET_PROJECT="${TARGET_PROJECT:-ongc-hr-finance-agent}"
export GOOGLE_GENAI_USE_VERTEXAI="TRUE"
export YUKTI_BACKEND_URL="http://127.0.0.1:8095"
export PORT="${PORT:-8080}"
export HOST="0.0.0.0"

echo "[yukti-cloudrun] Starting FastAPI + ADK + Gemini Live backend on 127.0.0.1:8095..."
cd /app/yukti/backend
/app/yukti/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8095 &
BACKEND_PID=$!

# Wait for backend health
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8095/health >/dev/null 2>&1; then
    echo "[yukti-cloudrun] Backend healthy on :8095"
    break
  fi
  sleep 1
done

echo "[yukti-cloudrun] Starting Next.js + WebSocket single-origin server on 0.0.0.0:${PORT}..."
cd /app/yukti/frontend
exec env NODE_ENV=production PORT="${PORT}" HOST="0.0.0.0" YUKTI_BACKEND_URL="http://127.0.0.1:8095" node server.js
