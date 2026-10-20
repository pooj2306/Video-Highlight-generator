@echo off
title Video Highlight Generator
cd /d "%~dp0"

echo ========================================================
echo       AI Video Highlight Generator
echo ========================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at venv\Scripts\python.exe
    echo Please make sure the venv folder is in the project root.
    echo.
    pause
    exit /b 1
)

echo [1/2] Virtual environment verified (venv\Scripts\python.exe)
echo [2/2] Starting server at http://127.0.0.1:8000 ...
echo.
echo ========================================================
echo Open in browser: http://127.0.0.1:8000
echo Press Ctrl+C in this window anytime to stop the server.
echo ========================================================
echo.

start "" "http://127.0.0.1:8000"
venv\Scripts\python.exe -m uvicorn app.server:app --host 127.0.0.1 --port 8000 --reload --reload-dir app --reload-dir src

if %ERRORLEVEL% neq 0 (
    echo.
    echo Server closed.
    pause
)
