#!/usr/bin/env bash
# ==============================================================================
# EC2 Monitoring and Incident Analysis System
# Unified startup and orchestration script
# ==============================================================================
# Usage:
#   ./start.sh          # Start Backend + Frontend + Agent concurrently
#   ./start.sh dev      # Start Backend + Frontend only
#   ./start.sh backend  # Start FastAPI Backend only
#   ./start.sh frontend # Start React Frontend only
#   ./start.sh agent    # Start Monitoring Agent only
#   ./start.sh setup    # Install all dependencies and prepare environments
# ==============================================================================

set -eo pipefail

# ANSI color codes
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
RESET='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
AGENT_DIR="${ROOT_DIR}/agent"

PIDS=()

log_info() {
    echo -e "${CYAN}[INFO]${RESET} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${RESET} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${RESET} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${RESET} $1"
}

# Resolve Python binary
find_python() {
    if command -v python3 &>/dev/null; then
        echo "python3"
    elif command -v python &>/dev/null; then
        echo "python"
    else
        log_error "Python 3 is required but not found in PATH."
        exit 1
    fi
}

# Resolve npm binary
find_npm() {
    if command -v npm &>/dev/null; then
        echo "npm"
    else
        log_error "npm is required for frontend but not found in PATH."
        exit 1
    fi
}

get_venv_python() {
    local target_dir="$1"
    if [ -f "${target_dir}/venv/bin/python" ]; then
        echo "${target_dir}/venv/bin/python"
    elif [ -f "${target_dir}/venv/Scripts/python.exe" ]; then
        echo "${target_dir}/venv/Scripts/python.exe"
    elif [ -f "${target_dir}/venv/Scripts/python" ]; then
        echo "${target_dir}/venv/Scripts/python"
    else
        echo ""
    fi
}

cleanup() {
    if [ ${#PIDS[@]} -gt 0 ]; then
        echo ""
        log_info "Received stop signal. Terminating child processes..."
        for pid in "${PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        done
        wait 2>/dev/null || true
        log_success "All services stopped cleanly."
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# ------------------------------------------------------------------------------
# Component Setup Functions
# ------------------------------------------------------------------------------

setup_backend() {
    log_info "Preparing Backend..."
    local py
    py="$(find_python)"

    cd "${BACKEND_DIR}"

    # Check/Create virtualenv
    if [ ! -d "venv" ]; then
        log_info "Creating backend virtualenv..."
        "$py" -m venv venv
    fi

    local vpy
    vpy="$(get_venv_python "${BACKEND_DIR}")"
    if [ -z "$vpy" ]; then
        log_error "Could not find python executable in backend/venv."
        exit 1
    fi

    log_info "Installing backend dependencies..."
    "$vpy" -m pip install -q --upgrade pip
    "$vpy" -m pip install -q -r requirements.txt

    # Environment file check
    if [ ! -f ".env" ]; then
        log_warn "backend/.env not found — copying from .env.example"
        cp .env.example .env
    fi

    # Database migrations
    log_info "Running Alembic migrations..."
    if ! "$vpy" -m alembic upgrade head 2>&1; then
        log_warn "Alembic migration skipped or failed (PostgreSQL may be offline)."
        log_warn "To run local Postgres: docker compose up -d db"
    else
        log_success "Database migrations up to date."
    fi
}

setup_frontend() {
    log_info "Preparing Frontend..."
    local npm_bin
    npm_bin="$(find_npm)"

    cd "${FRONTEND_DIR}"

    if [ ! -f ".env" ]; then
        log_warn "frontend/.env not found — copying from .env.example"
        cp .env.example .env
    fi

    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies (npm install)..."
        "$npm_bin" install
    fi
}

setup_agent() {
    log_info "Preparing Monitoring Agent..."
    local py
    py="$(find_python)"

    cd "${AGENT_DIR}"

    if [ ! -d "venv" ]; then
        log_info "Creating agent virtualenv..."
        "$py" -m venv venv
    fi

    local vpy
    vpy="$(get_venv_python "${AGENT_DIR}")"
    if [ -z "$vpy" ]; then
        log_error "Could not find python executable in agent/venv."
        exit 1
    fi

    log_info "Installing agent dependencies..."
    "$vpy" -m pip install -q --upgrade pip
    "$vpy" -m pip install -q -r requirements.txt

    if [ ! -f ".env" ]; then
        log_warn "agent/.env not found — copying from .env.example"
        cp .env.example .env
    fi
}

# ------------------------------------------------------------------------------
# Component Run Functions
# ------------------------------------------------------------------------------

start_backend() {
    log_info "Starting FastAPI Backend on http://localhost:8000 ..."
    cd "${BACKEND_DIR}"
    local vpy
    vpy="$(get_venv_python "${BACKEND_DIR}")"
    if [ -z "$vpy" ]; then
        setup_backend
        vpy="$(get_venv_python "${BACKEND_DIR}")"
    fi

    "$vpy" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    PIDS+=("$!")
}

start_frontend() {
    log_info "Starting Vite Frontend on http://localhost:5173 ..."
    cd "${FRONTEND_DIR}"
    local npm_bin
    npm_bin="$(find_npm)"
    if [ ! -d "node_modules" ]; then
        setup_frontend
    fi

    "$npm_bin" run dev -- --host 0.0.0.0 --port 5173 &
    PIDS+=("$!")
}

start_agent() {
    log_info "Starting Monitoring Agent..."
    cd "${AGENT_DIR}"
    local vpy
    vpy="$(get_venv_python "${AGENT_DIR}")"
    if [ -z "$vpy" ]; then
        setup_agent
        vpy="$(get_venv_python "${AGENT_DIR}")"
    fi

    # Wait briefly for backend to initialize
    sleep 3
    "$vpy" monitor_agent.py &
    PIDS+=("$!")
}

# ------------------------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------------------------

echo -e "${BOLD}${MAGENTA}"
echo "=================================================================="
echo "      EC2 Monitoring and Incident Analysis System                 "
echo "=================================================================="
echo -e "${RESET}"

MODE="${1:-all}"

case "$MODE" in
    setup)
        setup_backend
        setup_frontend
        setup_agent
        log_success "Setup complete for all components!"
        exit 0
        ;;
    backend)
        setup_backend
        start_backend
        wait
        ;;
    frontend)
        setup_frontend
        start_frontend
        wait
        ;;
    agent)
        setup_agent
        start_agent
        wait
        ;;
    dev)
        log_info "Starting in DEV mode (Backend + Frontend)..."
        setup_backend
        setup_frontend
        start_backend
        start_frontend
        echo ""
        log_success "Dev services running:"
        echo "  - Backend API:    http://localhost:8000"
        echo "  - Swagger Docs:   http://localhost:8000/docs"
        echo "  - Frontend UI:    http://localhost:5173"
        echo ""
        log_info "Press Ctrl+C to stop all services."
        wait
        ;;
    all|*)
        log_info "Starting in FULL mode (Backend + Frontend + Agent)..."
        setup_backend
        setup_frontend
        setup_agent
        start_backend
        start_frontend
        start_agent
        echo ""
        log_success "All services running:"
        echo "  - Backend API:    http://localhost:8000"
        echo "  - Swagger Docs:   http://localhost:8000/docs"
        echo "  - Frontend UI:    http://localhost:5173"
        echo "  - Agent Status:   Collecting & forwarding every 30s"
        echo ""
        log_info "Press Ctrl+C to stop all services."
        wait
        ;;
esac
