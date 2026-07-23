@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python 3.12 or newer was not found. Install it from https://python.org/
        pause
        exit /b 1
    )
    echo [1/3] Creating SonicDNA virtual environment with Python 3...
    py -3 --version
    py -3 -m venv .venv
    if errorlevel 1 goto :error
    echo [1/3] Virtual environment created at %CD%\.venv
)

set "dependency_stamp=.venv\.sonicdna-dependencies.sha256"
for /f "delims=" %%H in ('.venv\Scripts\python.exe -c "import hashlib,json,tomllib; d=tomllib.load(open('pyproject.toml','rb'))['project']; print(hashlib.sha256(json.dumps([d.get('requires-python'),d.get('dependencies',[])],sort_keys=True).encode()).hexdigest())"') do set "current_dependencies=%%H"
if not defined current_dependencies goto :error
set "installed_dependencies="
if exist "%dependency_stamp%" set /p "installed_dependencies="<"%dependency_stamp%"

set "dependencies_ready=1"
if not "!current_dependencies!"=="!installed_dependencies!" set "dependencies_ready=0"
if "!dependencies_ready!"=="1" (
    ".venv\Scripts\python.exe" -c "import importlib.metadata as m; m.version('sonicdna')" >nul 2>nul
    if errorlevel 1 set "dependencies_ready=0"
)
if "!dependencies_ready!"=="1" (
    ".venv\Scripts\python.exe" -m pip check >nul 2>nul
    if errorlevel 1 set "dependencies_ready=0"
)

if "!dependencies_ready!"=="0" (
    echo [2/3] Installing SonicDNA and its dependencies. This can take several minutes...
    ".venv\Scripts\python.exe" -m pip install --verbose --progress-bar on -e .
    if errorlevel 1 goto :error
    >"%dependency_stamp%" echo !current_dependencies!
    echo [2/3] Dependency installation completed.
) else (
    echo [2/3] Python dependency requirements are up to date.
)

echo [3/3] Setup complete. Starting Warbeats SonicDNA...

if /I "%~1"=="--debug" (
    echo Starting Warbeats SonicDNA in debug mode...
    echo The application console will remain visible until you close this window.
    ".venv\Scripts\python.exe" -m sonicdna
    set "exit_code=!errorlevel!"
    echo.
    echo Warbeats SonicDNA exited with code !exit_code!.
    pause
    exit /b !exit_code!
)

if "%~1"=="" (
    start "SonicDNA" ".venv\Scripts\pythonw.exe" -m sonicdna
    exit /b 0
)

".venv\Scripts\python.exe" -m sonicdna %*
set "exit_code=%errorlevel%"
if not "%exit_code%"=="0" pause
exit /b %exit_code%

:error
echo SonicDNA setup failed.
pause
exit /b 1
