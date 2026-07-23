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
$dependencyStamp = Join-Path $PSScriptRoot ".venv\.sonicdna-dependencies.sha256"
$currentDependencies = & $python -c "import hashlib,json,tomllib; d=tomllib.load(open('pyproject.toml','rb'))['project']; print(hashlib.sha256(json.dumps([d.get('requires-python'),d.get('dependencies',[])],sort_keys=True).encode()).hexdigest())"
if ($LASTEXITCODE -ne 0 -or -not $currentDependencies) {
    throw "Unable to read SonicDNA dependency requirements."
}
$installedDependencies = if (Test-Path -LiteralPath $dependencyStamp) {
    (Get-Content -LiteralPath $dependencyStamp -Raw).Trim()
} else {
    ""
}
$dependenciesReady = $currentDependencies -eq $installedDependencies
if ($dependenciesReady) {
    & $python -c "import importlib.metadata as m; m.version('sonicdna')" 2>$null
    $dependenciesReady = $LASTEXITCODE -eq 0
}
if ($dependenciesReady) {
    & $python -m pip check *> $null
    $dependenciesReady = $LASTEXITCODE -eq 0
}
if (-not $dependenciesReady) {
    Write-Host "[2/3] Installing SonicDNA and its dependencies. This can take several minutes..."
    & $python -m pip install --verbose --progress-bar on -e .
    if ($LASTEXITCODE -ne 0) {
        throw "SonicDNA dependency installation failed with exit code $LASTEXITCODE."
    }
    Set-Content -LiteralPath $dependencyStamp -Value $currentDependencies -Encoding ascii
    Write-Host "[2/3] Dependency installation completed."
} else {
    Write-Host "[2/3] Python dependency requirements are up to date."
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
