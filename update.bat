@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" update.py %*
) else (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python 3.12 or newer was not found.
        pause
        exit /b 1
    )
    py -3 update.py %*
)

set "exit_code=%errorlevel%"
if not "%exit_code%"=="0" pause
exit /b %exit_code%
