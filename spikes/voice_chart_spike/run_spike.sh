#!/usr/bin/env bash
# ==============================================================================
# ONGC HR & Finance: Voice-to-Chart Spike Launcher
# Boots FastAPI Backend (port 8100) and Next.js Frontend (port 3100)
# ==============================================================================

set -e

SPIKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SPIKE_DIR}/backend"
FRONTEND_DIR="${SPIKE_DIR}/frontend"

echo "======================================================================"
echo "    ONGC HR & Finance: Voice-to-Chart Spike (Gemini Live + ECharts)   "
echo "======================================================================"

export PATH="$HOME/.local/bin:$PATH"

command -v uv >/dev/null 2>&1 || { echo "[!] Error: uv is required."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "[!] Error: node is required."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "[!] Error: npm is required."; exit 1; }

# Clean up any child processes on exit
cleanup() {
    echo ""
    echo "[*] Stopping Spike services..."
    if [ -n "${BACKEND_PID}" ]; then
        kill "${BACKEND_PID}" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID}" ]; then
        kill "${FRONTEND_PID}" 2>/dev/null || true
    fi
    echo "[✓] All Spike services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start Backend
echo "[*] Starting FastAPI Backend on http://localhost:8100..."
(cd "${BACKEND_DIR}" && PORT=8100 exec uv run python run.py) &
BACKEND_PID=$!

# Wait for backend health check
echo "[*] Waiting for backend readiness..."
for i in {1..30}; do
    if curl -s http://localhost:8100/api/health >/dev/null 2>&1; then
        echo "[✓] Backend is ready!"
        break
    fi
    sleep 0.5
done

# 2. Start Frontend
echo "[*] Starting Next.js Frontend on http://localhost:3100..."
(cd "${FRONTEND_DIR}" && exec npm run start) &
FRONTEND_PID=$!

echo "======================================================================"
echo "[✓] Voice-to-Chart Spike is running!"
echo "    • Frontend UI: http://localhost:3100"
echo "    • Backend API: http://localhost:8100"
echo "    • Health:      http://localhost:8100/api/health"
echo "======================================================================"
echo "Press Ctrl+C to stop all services."

wait
