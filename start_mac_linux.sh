#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[[ -f backend/.env ]] || cp backend/.env.example backend/.env
if [[ ! -x backend/.venv/bin/python ]]; then
  python3 -m venv backend/.venv
fi
backend/.venv/bin/python -m pip install -r backend/requirements.txt
if [[ ! -d frontend/node_modules ]]; then
  (cd frontend && npm install)
fi
cleanup(){ kill "$API_PID" "$WEB_PID" 2>/dev/null || true; wait "$API_PID" "$WEB_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
(cd backend && .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) & API_PID=$!
(cd frontend && npm run dev) & WEB_PID=$!
echo 'Open http://localhost:5173 in your browser (keep terminal open).'
wait
