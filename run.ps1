# PowerShell startup script for AI Video Highlight Generator
Set-Location $PSScriptRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       AI Video Highlight Generator" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$py = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "[ERROR] Virtual environment not found at: $py" -ForegroundColor Red
    Write-Host "Please ensure venv exists in this folder." -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Using virtual environment Python: $py" -ForegroundColor Green
Write-Host "[OK] Launching web application at http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server anytime.`n" -ForegroundColor Gray

Start-Process "http://127.0.0.1:8000"
& $py -m uvicorn app.server:app --host 127.0.0.1 --port 8000 --reload --reload-dir app --reload-dir src
