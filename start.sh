#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "[1/3] Creating SonicDNA virtual environment with Python 3..."
    python3 --version
    python3 -m venv .venv
    echo "[1/3] Virtual environment created at $(pwd)/.venv"
fi

echo "[2/3] Checking required Python libraries..."
dependency_stamp=".venv/.sonicdna-dependencies.sha256"
current_dependencies=$(.venv/bin/python -c "import hashlib,json,tomllib; d=tomllib.load(open('pyproject.toml','rb'))['project']; print(hashlib.sha256(json.dumps([d.get('requires-python'),d.get('dependencies',[])],sort_keys=True).encode()).hexdigest())")
installed_dependencies=""
if [ -f "$dependency_stamp" ]; then
    installed_dependencies=$(tr -d '\r\n' < "$dependency_stamp")
fi

dependencies_ready=true
if [ "$current_dependencies" != "$installed_dependencies" ]; then
    dependencies_ready=false
elif ! .venv/bin/python -c "import importlib.metadata as m; m.version('sonicdna')" >/dev/null 2>&1; then
    dependencies_ready=false
elif ! .venv/bin/python -m pip check >/dev/null 2>&1; then
    dependencies_ready=false
fi

if [ "$dependencies_ready" = false ]; then
    echo "[2/3] Installing SonicDNA and its dependencies. This can take several minutes..."
    .venv/bin/python -m pip install --verbose --progress-bar on -e .
    printf '%s\n' "$current_dependencies" > "$dependency_stamp"
    echo "[2/3] Dependency installation completed."
else
    echo "[2/3] Python dependency requirements are up to date."
fi

echo "[3/3] Starting Warbeats SonicDNA..."

if [ "${1:-}" = "--debug" ]; then
    echo "Starting Warbeats SonicDNA in debug mode..."
    exec .venv/bin/python -m sonicdna
fi

exec .venv/bin/python -m sonicdna "$@"
