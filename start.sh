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

# Locate virtual environment python binary (works across Windows Git Bash, WSL, and Linux/macOS)
if [ -f "$BACKEND_DIR/venv/Scripts/python.exe" ]; then
    VENV_PYTHON="$BACKEND_DIR/venv/Scripts/python.exe"
elif [ -f "$BACKEND_DIR/venv/bin/python" ]; then
    VENV_PYTHON="$BACKEND_DIR/venv/bin/python"
elif [ -f "$BACKEND_DIR/venv/Scripts/python" ]; then
    VENV_PYTHON="$BACKEND_DIR/venv/Scripts/python"
else
    # Attempt to create venv if missing
    echo "[INFO] Initializing Python virtual environment..."
    PYTHON_CMD="python3"
    if ! command -v python3 &>/dev/null; then
        PYTHON_CMD="python"
    fi
    (cd "$BACKEND_DIR" && $PYTHON_CMD -m venv venv)

    if [ -f "$BACKEND_DIR/venv/Scripts/python.exe" ]; then
        VENV_PYTHON="$BACKEND_DIR/venv/Scripts/python.exe"
    elif [ -f "$BACKEND_DIR/venv/bin/python" ]; then
        VENV_PYTHON="$BACKEND_DIR/venv/bin/python"
    else
        VENV_PYTHON="python"
    fi
fi

case "$MODE" in
    setup)
        echo "[INFO] Running full setup..."
        cd "$BACKEND_DIR"
        "$VENV_PYTHON" -m pip install -q -r requirements.txt
        "$VENV_PYTHON" -m alembic upgrade head

        cd "$FRONTEND_DIR"
        if [ ! -d "node_modules" ]; then npm install; fi
        echo "[SUCCESS] Setup complete."
        ;;

    backend)
        echo "[INFO] Starting Backend..."
        cd "$BACKEND_DIR"
        "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
        ;;

    frontend)
        echo "[INFO] Starting Frontend..."
        cd "$FRONTEND_DIR"
        npm run dev
        ;;

    test)
        echo "[INFO] Running tests..."
        cd "$BACKEND_DIR"
        "$VENV_PYTHON" -m pytest app/tests/ -v
        ;;

    all|dev|*)
        echo "[INFO] Starting Backend and Frontend..."
        cd "$BACKEND_DIR"
        "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
        BACKEND_PID=$!

        cd "$FRONTEND_DIR"
        npm run dev &
        FRONTEND_PID=$!

        echo "[SUCCESS] Services launched:"
        echo "  - Backend API:  http://localhost:8000"
        echo "  - Frontend UI:  http://localhost:5173"
        echo "  - Swagger Docs: http://localhost:8000/docs"

        trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM
        wait
        ;;
esac
