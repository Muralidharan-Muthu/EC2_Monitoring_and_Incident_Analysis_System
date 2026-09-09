#!/usr/bin/env bash
# ==================================================================
#       EC2 Monitoring and Incident Analysis System                 
#       (Agentless SSH-Based Remote EC2 Telemetry)
# ==================================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

MODE="${1:-all}"

# Ensure .env files exist
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "[INFO] Copying backend/.env.example to backend/.env"
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

if [ ! -f "$FRONTEND_DIR/.env" ]; then
    echo "[INFO] Copying frontend/.env.example to frontend/.env"
    cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env"
fi

case "$MODE" in
    setup)
        echo "[INFO] Running full setup..."
        cd "$BACKEND_DIR"
        if [ ! -d "venv" ]; then python3 -m venv venv; fi
        source venv/bin/activate
        pip install -q -r requirements.txt
        alembic upgrade head

        cd "$FRONTEND_DIR"
        if [ ! -d "node_modules" ]; then npm install; fi
        echo "[SUCCESS] Setup complete."
        ;;

    backend)
        echo "[INFO] Starting Backend..."
        cd "$BACKEND_DIR"
        source venv/bin/activate
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
        ;;

    frontend)
        echo "[INFO] Starting Frontend..."
        cd "$FRONTEND_DIR"
        npm run dev
        ;;

    test)
        echo "[INFO] Running tests..."
        cd "$BACKEND_DIR"
        source venv/bin/activate
        pytest app/tests/ -v
        ;;

    all|dev|*)
        echo "[INFO] Starting Backend and Frontend..."
        cd "$BACKEND_DIR"
        source venv/bin/activate
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
        BACKEND_PID=$!

        cd "$FRONTEND_DIR"
        npm run dev &
        FRONTEND_PID=$!

        echo "[SUCCESS] Services launched:"
        echo "  - Backend:  http://localhost:8000"
        echo "  - Frontend: http://localhost:5173"
        echo "  - Swagger:  http://localhost:8000/docs"

        trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM
        wait
        ;;
esac
