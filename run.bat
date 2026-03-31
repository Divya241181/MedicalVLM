@echo off
setlocal enabledelayedexpansion

echo [SYSTEM] Starting MedVLM Platform Unified Controller...
echo.

:: --- CONFIGURATION ---
set BACKEND_PORT=8000
set FRONTEND_PORT=5173
set BACKEND_URL=http://localhost:%BACKEND_PORT%
set FRONTEND_URL=http://localhost:%FRONTEND_PORT%

:: --- DEPENDENCY CHECKS ---
if not exist ".env" (
    echo [ERROR] Root .env file missing!
    pause
    exit /b
)

if not exist "venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] venv creation failed.
        pause
        exit /b
    )
)

if not exist "frontend\node_modules" (
    echo [INFO] installing node modules...
    cd frontend && npm install && cd ..
)

:: --- START SERVICES ---
echo.
echo [1/2] Launching LLaVA-1.5 Backend (Port %BACKEND_PORT%)...
start "MedVLM Backend" cmd /c ".\venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"

echo [2/2] Launching React 19 Frontend (Port %FRONTEND_PORT%)...
start "MedVLM Frontend" cmd /c "cd frontend && npm run dev"

:: --- WAIT & OPEN BROWSER ---
echo.
echo [INFO] Waiting for services to initialize...
timeout /t 5 /nobreak > nul

echo [SUCCESS] Opening MedVLM Interface...
start "" "%FRONTEND_URL%"

echo.
echo  ------------------------------------------------------------------
echo   Services are running in separate windows.
echo   - Frontend: %FRONTEND_URL%
echo   - API Docs: %BACKEND_URL%/docs
echo  ------------------------------------------------------------------
echo.
echo   Press any key to stop this controller (Services will remain open).
pause > nul
