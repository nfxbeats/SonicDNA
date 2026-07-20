#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "Creating SonicDNA virtual environment..."
    python3 -m venv .venv
fi

if ! .venv/bin/python -c "import librosa, numpy, PySide6, scipy, sklearn, soundfile" >/dev/null 2>&1; then
    echo "Installing SonicDNA and its dependencies..."
    .venv/bin/python -m pip install -e .
fi

exec .venv/bin/python -m sonicdna "$@"
