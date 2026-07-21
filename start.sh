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
if ! .venv/bin/python -c "import librosa, numpy, PySide6, scipy, sklearn, soundfile" >/dev/null 2>&1; then
    echo "[2/3] Installing SonicDNA and its dependencies. This can take several minutes..."
    .venv/bin/python -m pip install --verbose --progress-bar on -e .
    echo "[2/3] Dependency installation completed."
else
    echo "[2/3] Required Python libraries are already installed."
fi

echo "[3/3] Starting Warbeats SonicDNA..."

if [ "${1:-}" = "--debug" ]; then
    echo "Starting Warbeats SonicDNA in debug mode..."
    exec .venv/bin/python -m sonicdna
fi

exec .venv/bin/python -m sonicdna "$@"
