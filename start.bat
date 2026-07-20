@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python 3.12 or newer was not found. Install it from https://python.org/
        pause
        exit /b 1
    )
    echo Creating SonicDNA virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -c "import librosa, numpy, PySide6, scipy, sklearn, soundfile" >nul 2>nul
if errorlevel 1 (
    echo Installing SonicDNA and its dependencies...
    ".venv\Scripts\python.exe" -m pip install -e .
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -m sonicdna %*
set "exit_code=%errorlevel%"
if not "%exit_code%"=="0" pause
exit /b %exit_code%

:error
echo SonicDNA setup failed.
pause
exit /b 1
