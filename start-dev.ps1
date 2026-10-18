# ==============================================================================
# Smart Fridge AI - Local Development Startup Script
# ==============================================================================
# Launches both the FastAPI Backend (127.0.0.1:8000) and Vite Frontend (localhost:5173)
# in separate PowerShell windows with health checking and duplicate-port protection.
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$NoNewWindow,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$KillExisting
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Starting Smart Fridge AI Development Environment       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray

# ------------------------------------------------------------------------------
# 1. Directory and Dependency Verification
# ------------------------------------------------------------------------------
if (-not (Test-Path $BackendDir)) {
    Write-Host "ERROR: Backend directory not found at $BackendDir" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $FrontendDir)) {
    Write-Host "ERROR: Frontend directory not found at $FrontendDir" -ForegroundColor Red
    exit 1
}

# Python virtual environment
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $AltVenv = Join-Path $BackendDir "venv\Scripts\python.exe"
    if (Test-Path $AltVenv) {
        $VenvPython = $AltVenv
    } else {
        Write-Host "ERROR: Python virtual environment not found in $BackendDir\.venv" -ForegroundColor Red
        Write-Host "Please create one using: cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
        exit 1
    }
}

# Node.js and npm
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js is not found in your system PATH. Please install Node.js from https://nodejs.org" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: npm is not found in your system PATH." -ForegroundColor Red
    exit 1
}

# Ensure .env exists in backend (copy from .env.example if missing)
$BackendEnv = Join-Path $BackendDir ".env"
$BackendEnvExample = Join-Path $BackendDir ".env.example"
if (-not (Test-Path $BackendEnv) -and (Test-Path $BackendEnvExample)) {
    Write-Host "Notice: .env not found in backend. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item $BackendEnvExample $BackendEnv
}

# ------------------------------------------------------------------------------
# 2. Check Port 8000 (Backend)
# ------------------------------------------------------------------------------
$SkipBackendLaunch = $false
$ExistingBackend = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 } | Select-Object -First 1

if ($ExistingBackend -and $KillExisting) {
    Write-Host "Terminating process on port 8000 (PID: $($ExistingBackend.OwningProcess))..." -ForegroundColor Yellow
    Stop-Process -Id $ExistingBackend.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    $ExistingBackend = $null
}

if ($ExistingBackend -and -not $FrontendOnly) {
    # Check if backend is already responding to /health
    try {
        $check = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
        if ($check.status -in @("healthy", "degraded")) {
            Write-Host "Notice: Backend is already running and healthy on http://127.0.0.1:8000 (PID: $($ExistingBackend.OwningProcess))." -ForegroundColor Green
            $SkipBackendLaunch = $true
        }
    } catch {
        Write-Host "Warning: Port 8000 is occupied by PID $($ExistingBackend.OwningProcess) but not responding to health check." -ForegroundColor Yellow
        Write-Host "Use -KillExisting to stop conflicting processes, or terminate PID $($ExistingBackend.OwningProcess) manually." -ForegroundColor Yellow
    }
}

# ------------------------------------------------------------------------------
# 3. Check Port 5173 (Frontend)
# ------------------------------------------------------------------------------
$SkipFrontendLaunch = $false
$ExistingFrontend = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 } | Select-Object -First 1

if ($ExistingFrontend -and $KillExisting) {
    Write-Host "Terminating process on port 5173 (PID: $($ExistingFrontend.OwningProcess))..." -ForegroundColor Yellow
    Stop-Process -Id $ExistingFrontend.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    $ExistingFrontend = $null
}

if ($ExistingFrontend -and -not $BackendOnly) {
    Write-Host "Notice: Frontend is already running on http://localhost:5173 (PID: $($ExistingFrontend.OwningProcess))." -ForegroundColor Green
    $SkipFrontendLaunch = $true
}

# ------------------------------------------------------------------------------
# 4. Start Backend (if not already running)
# ------------------------------------------------------------------------------
if (-not $FrontendOnly -and -not $SkipBackendLaunch) {
    Write-Host "`n--> Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
    
    if ($NoNewWindow) {
        Write-Host "Running backend in current process..." -ForegroundColor Gray
        Push-Location $BackendDir
        & $VenvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
        Pop-Location
        exit 0
    } else {
        $BackendCmd = "cd '$BackendDir'; try { `$Host.UI.RawUI.WindowTitle = '[Smart Fridge AI] Backend API (Port 8000)' } catch {}; & '$VenvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
        Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $BackendCmd
    }
}

# ------------------------------------------------------------------------------
# 5. Wait for Backend Health (if starting backend)
# ------------------------------------------------------------------------------
if (-not $FrontendOnly -and -not $SkipBackendLaunch) {
    Write-Host "Waiting for backend server and AI models to initialize..." -NoNewline -ForegroundColor Gray
    $Attempts = 0
    $BackendHealthy = $false
    while ($Attempts -lt 30) {
        Start-Sleep -Seconds 1
        $Attempts++
        Write-Host "." -NoNewline -ForegroundColor Gray
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
            if ($response.status -in @("healthy", "degraded")) {
                $BackendHealthy = $true
                break
            }
        } catch {
            # Still initializing
        }
    }
    Write-Host ""
    if ($BackendHealthy) {
        Write-Host "Backend is online and ready!" -ForegroundColor Green
    } else {
        Write-Host "Warning: Backend is taking longer than expected to start." -ForegroundColor Yellow
        Write-Host "Please check the Backend PowerShell window for any model loading or port binding errors." -ForegroundColor Yellow
    }
}

# ------------------------------------------------------------------------------
# 6. Start Frontend (if not already running)
# ------------------------------------------------------------------------------
if (-not $BackendOnly -and -not $SkipFrontendLaunch) {
    Write-Host "`n--> Launching Vite Frontend on http://localhost:5173..." -ForegroundColor Green
    
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host "node_modules not found in frontend. Running 'npm install'..." -ForegroundColor Yellow
        Push-Location $FrontendDir
        npm install
        Pop-Location
    }
    
    $FrontendCmd = "cd '$FrontendDir'; try { `$Host.UI.RawUI.WindowTitle = '[Smart Fridge AI] Frontend (Port 5173)' } catch {}; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $FrontendCmd
}

# ------------------------------------------------------------------------------
# 7. Summary
# ------------------------------------------------------------------------------
Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "   Smart Fridge AI Development Servers Ready              " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Frontend:    http://localhost:5173" -ForegroundColor White
Write-Host "  Backend API: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  API Docs:    http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  Health:      http://127.0.0.1:8000/health" -ForegroundColor White
Write-Host "==========================================================`n" -ForegroundColor Cyan
