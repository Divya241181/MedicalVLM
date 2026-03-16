@echo off
title MedicalVLM App Launcher
echo ===================================================
echo     Starting Medical VLM Application
echo ===================================================
echo.

echo [1/2] Starting Backend API (Port 8001)...
:: The 'start' command opens a new command prompt window for the backend
start "MedicalVLM Backend" cmd /k ".\venv\Scripts\python.exe -m uvicorn backend.api.main:app --reload --port 8001"

echo [2/2] Starting Frontend React App (Port 5173)...
:: Open another new window for the frontend
start "MedicalVLM Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo     All Services Started in Separate Windows!
echo ===================================================
echo.
echo - Frontend: http://localhost:5173
echo - Backend:  http://localhost:8001/docs
echo.
echo You can safely close THIS window. Leave the other two open.
pause
