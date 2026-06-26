#!/bin/bash
set -e

echo "=== Starting Placement Cell Resume Builder ==="

# Backend
echo "[1/2] Setting up backend..."
cd "$(dirname "$0")/backend"

if [ ! -d "venv" ]; then
  python3 -m venv venv
  venv/bin/pip install -r requirements.txt -q
fi

venv/bin/uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend running at http://localhost:8000 (PID $BACKEND_PID)"

# Frontend
echo "[2/2] Starting frontend..."
cd ../frontend
npm install -q
npm run dev &
FRONTEND_PID=$!
echo ""
echo "Open http://localhost:5173 in your browser."
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
