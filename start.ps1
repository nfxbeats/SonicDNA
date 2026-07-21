$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    Write-Host "[1/3] Creating SonicDNA virtual environment with Python 3..."
    py -3 --version
    py -3 -m venv .venv
    Write-Host "[1/3] Virtual environment created at $PSScriptRoot\.venv"
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
Write-Host "[2/3] Checking required Python libraries..."
& $python -c "import librosa, numpy, PySide6, scipy, sklearn, soundfile" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[2/3] Installing SonicDNA and its dependencies. This can take several minutes..."
    & $python -m pip install --verbose --progress-bar on -e .
    Write-Host "[2/3] Dependency installation completed."
} else {
    Write-Host "[2/3] Required Python libraries are already installed."
}
Write-Host "[3/3] Starting Warbeats SonicDNA..."

if ($args.Count -eq 1 -and $args[0] -eq "--debug") {
    Write-Host "Starting Warbeats SonicDNA in debug mode..."
    & $python -m sonicdna
    $debugExitCode = $LASTEXITCODE
    Write-Host "Warbeats SonicDNA exited with code $debugExitCode."
    Read-Host "Press Enter to close"
    exit $debugExitCode
}
& $python -m sonicdna @args
exit $LASTEXITCODE
