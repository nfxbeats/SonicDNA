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
& $python -m sonicdna @args
exit $LASTEXITCODE
