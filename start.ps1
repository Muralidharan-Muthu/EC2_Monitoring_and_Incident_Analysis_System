<#
.SYNOPSIS
    EC2 Monitoring and Incident Analysis System - Startup Script
.DESCRIPTION
    Launches Backend, Frontend, and Monitoring Agent.
.PARAMETER Mode
    setup, dev, backend, frontend, agent, all (default)
#>
param(
    [ValidateSet("all", "dev", "backend", "frontend", "agent", "setup")]
    [string]$Mode = "all"
)

$RootDir = $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$AgentDir = Join-Path $RootDir "agent"

Write-Host "==================================================================" -ForegroundColor Magenta
Write-Host "      EC2 Monitoring and Incident Analysis System                 " -ForegroundColor Magenta
Write-Host "==================================================================" -ForegroundColor Magenta
Write-Host ""

function Ensure-EnvFiles {
    if (-not (Test-Path (Join-Path $BackendDir ".env"))) {
        Write-Host "[INFO] Copying backend\.env.example to backend\.env" -ForegroundColor Cyan
        Copy-Item (Join-Path $BackendDir ".env.example") (Join-Path $BackendDir ".env")
    }
    if (-not (Test-Path (Join-Path $FrontendDir ".env"))) {
        Write-Host "[INFO] Copying frontend\.env.example to frontend\.env" -ForegroundColor Cyan
        Copy-Item (Join-Path $FrontendDir ".env.example") (Join-Path $FrontendDir ".env")
    }
    if (-not (Test-Path (Join-Path $AgentDir ".env"))) {
        Write-Host "[INFO] Copying agent\.env.example to agent\.env" -ForegroundColor Cyan
        Copy-Item (Join-Path $AgentDir ".env.example") (Join-Path $AgentDir ".env")
    }
}

Ensure-EnvFiles

switch ($Mode) {
    "setup" {
        Write-Host "[INFO] Setting up Backend..." -ForegroundColor Cyan
        Set-Location $BackendDir
        if (-not (Test-Path "venv")) { python -m venv venv }
        .\venv\Scripts\python.exe -m pip install -q -r requirements.txt
        .\venv\Scripts\python.exe -m alembic upgrade head

        Write-Host "[INFO] Setting up Frontend..." -ForegroundColor Cyan
        Set-Location $FrontendDir
        if (-not (Test-Path "node_modules")) { npm install }

        Write-Host "[INFO] Setting up Agent..." -ForegroundColor Cyan
        Set-Location $AgentDir
        if (-not (Test-Path "venv")) { python -m venv venv }
        .\venv\Scripts\python.exe -m pip install -q -r requirements.txt

        Set-Location $RootDir
        Write-Host "[SUCCESS] Setup complete!" -ForegroundColor Green
    }
    "backend" {
        Set-Location $BackendDir
        .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    }
    "frontend" {
        Set-Location $FrontendDir
        npm run dev
    }
    "agent" {
        Set-Location $AgentDir
        .\venv\Scripts\python.exe monitor_agent.py
    }
    "dev" {
        Write-Host "[INFO] Starting Backend and Frontend in separate windows..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$BackendDir'; .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$FrontendDir'; npm run dev"
        Write-Host "[SUCCESS] Dev servers launched!" -ForegroundColor Green
        Write-Host "  - Backend:  http://localhost:8000"
        Write-Host "  - Frontend: http://localhost:5173"
    }
    "all" {
        Write-Host "[INFO] Starting Backend, Frontend, and Agent in separate windows..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$BackendDir'; .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$FrontendDir'; npm run dev"
        Start-Sleep -Seconds 3
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$AgentDir'; .\venv\Scripts\python.exe monitor_agent.py"
        Write-Host "[SUCCESS] All services launched!" -ForegroundColor Green
        Write-Host "  - Backend:  http://localhost:8000"
        Write-Host "  - Frontend: http://localhost:5173"
        Write-Host "  - Agent:    Running in separate PowerShell window"
    }
}
