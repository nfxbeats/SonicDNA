# SonicDNA

SonicDNA is a local-first acoustic similarity search tool for audio samples. This repository
currently implements the Phase 3 desktop application, command-line search engine, and persistent
incremental index described in the project spec.

## Run on Windows

Python 3.12 or newer is required. The launcher creates `.venv` and installs dependencies on
its first run:

```powershell
.\start.bat
```

With no arguments, the launcher opens the SonicDNA desktop interface. Add one or more library
folders, choose or drop a query sample, and click **Find Similar**. Scanning and feature extraction
run in a background thread and can be cancelled safely.

The original command-line workflow remains available by supplying arguments:

```powershell
.\start.bat "C:\Samples\query.wav" "C:\Samples\Library" --limit 10
```

PowerShell users may instead run:

```powershell
.\start.ps1
```

## Run on macOS or Linux

```sh
chmod +x start.sh
./start.sh
```

Pass a query and library path to either launcher to use CLI mode.

## Desktop features

- Add and remove multiple recursively scanned library folders
- Incremental background indexing with progress and cancellation
- Browse for or drag-and-drop a query sample
- Ranked similarity results with relative scores from 0 to 100
- Query and result audio preview using Qt Multimedia; click, use Up/Down, double-click, press Space,
  or use Play Selected
- Persistent Auto-play selection option for mouse and keyboard result navigation
- Persistent preview-volume slider next to Auto-play selection
- Clicking the already-selected result restarts it from the beginning
- Low-latency `sounddevice` playback with resampling and 5 ms click-resistant transitions
- Automatic Qt Multimedia fallback when PortAudio or an output device is unavailable
- A playing-row indicator and immediate Stop control
- Drag one or more selected result files into compatible DAWs or the system file manager
- Right-click actions to play, reveal, open, copy the full path, or copy the filename
- CSV export of the current ranked results
- Popup Similarity Weights editor for Body/Pitch, Attack, Decay, Brightness, Timbre,
  Noise/Distortion, and Duration, with persisted kick defaults and Reset Defaults
- Persistent folders, window geometry, result count, and preview volume

The application uses `sonicdna-logo.png` as its runtime icon. The PNG is the cross-platform
master asset; `sonicdna.ico` is its Windows packaging derivative.

The first run can take several minutes while the scientific Python and Qt dependencies install.
Audio files are read for analysis only; SonicDNA never modifies them.

## Persistent index

The first search recursively analyzes the entire library and stores feature vectors in the
platform-specific SonicDNA application-data directory. Later searches inspect the folder but
only re-analyze new or modified files. Missing files are removed from the index.

Each run prints a scan summary such as:

```text
Scan: 906 found, 0 indexed, 905 unchanged, 0 removed
```

Use `--rebuild` to deliberately re-extract the entire selected library. To keep an index in a
specific location, use `--database D:\path\to\index.db`.

Scores are relative values from 0 to 100 and results are ordered from most to least similar.
They are useful for ranking, but are not calibrated probabilities or percentages.

## Development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
```
