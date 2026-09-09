<#
.SYNOPSIS
    EC2 Monitoring and Incident Analysis System - Startup Script (PowerShell)
.DESCRIPTION
    Launches Backend (FastAPI with automated SSH monitoring) and Frontend (React/Vite).
.PARAMETER Mode
    setup, dev, backend, frontend, test, all (default)
#>
param(
    [ValidateSet("all", "dev", "backend", "frontend", "test", "setup")]
    [string]$Mode = "all"
)

$RootDir = $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host "==================================================================" -ForegroundColor Magenta
Write-Host "      EC2 Monitoring and Incident Analysis System                 " -ForegroundColor Magenta
Write-Host "      (Agentless SSH-Based Remote EC2 Telemetry)                  " -ForegroundColor Cyan
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

        Set-Location $RootDir
        Write-Host "[SUCCESS] Setup complete!" -ForegroundColor Green
    }
    "backend" {
        Write-Host "[INFO] Starting Backend..." -ForegroundColor Cyan
        Set-Location $BackendDir
        .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
    }
    "frontend" {
        Write-Host "[INFO] Starting Frontend..." -ForegroundColor Cyan
        Set-Location $FrontendDir
        npm run dev
    }
    "test" {
        Write-Host "[INFO] Running full test suite..." -ForegroundColor Cyan
        Set-Location $BackendDir
        .\venv\Scripts\python.exe -m pytest app/tests/ -v
    }
    default {
        # 'all' or 'dev'
        Write-Host "[INFO] Launching FastAPI Backend and React Frontend in separate windows..." -ForegroundColor Cyan
        Start-Process wt -ArgumentList "-w 0 new-tab -d `"$BackendDir`" powershell -NoExit -Command `".\venv\Scripts\activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`"" -ErrorAction SilentlyContinue
        if ($LASTEXITCODE -ne 0) {
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$BackendDir`"; .\venv\Scripts\activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$FrontendDir`"; npm run dev"
        } else {
            Start-Process wt -ArgumentList "-w 0 new-tab -d `"$FrontendDir`" powershell -NoExit -Command `"npm run dev`""
        }
        Write-Host "[SUCCESS] Services launched:" -ForegroundColor Green
        Write-Host "  - Backend API:  http://localhost:8000" -ForegroundColor White
        Write-Host "  - Frontend UI:  http://localhost:5173" -ForegroundColor White
        Write-Host "  - Swagger Docs: http://localhost:8000/docs" -ForegroundColor White
    }
}
