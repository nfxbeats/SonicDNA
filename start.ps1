$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    Write-Host "Creating SonicDNA virtual environment..."
    py -3 -m venv .venv
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $python -c "import librosa, numpy, PySide6, scipy, sklearn, soundfile" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing SonicDNA and its dependencies..."
    & $python -m pip install -e .
}

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
