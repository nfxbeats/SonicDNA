# SonicDNA

SonicDNA is a local-first desktop application for finding acoustically similar audio samples. It
includes a graphical interface, command-line search, and a persistent incremental index.

## Installation

### Requirements

- Python 3.12 or newer
- Windows 10/11, a current macOS release, or a modern Linux desktop
- An available audio-output device for sample preview

Download or clone the project, then open a terminal in the SonicDNA directory. The supplied
launcher creates an isolated `.venv` virtual environment and installs SonicDNA and its Python
dependencies automatically on the first run. The initial installation can take several minutes.
The launchers display numbered setup stages, the selected Python version, dependency-check status,
and verbose pip download/build progress during installation.

On Windows:

```powershell
.\start.bat
```

When `start.bat` is run without arguments, it launches the desktop application through
`pythonw.exe` and immediately closes its CMD window. A command-line search with arguments remains
attached to the terminal so scan progress, results, and errors stay visible.

To launch the desktop interface with a persistent CMD window for debugging:

```powershell
.\start.bat --debug
```

Debug mode uses console Python, displays standard output and error messages while the GUI runs,
and pauses after the application exits so the final traceback or exit code remains visible.

Equivalent launcher commands are:

```powershell
.\start.ps1 --debug
```

```sh
./start.sh --debug
```

In Windows CMD, include the `.bat` extension: `start.bat --debug`. The bare command `start` is a
built-in Windows command and does not invoke SonicDNA's launcher.

Alternatively, use the PowerShell launcher:

```powershell
.\start.ps1
```

On macOS or Linux:

```sh
chmod +x start.sh
./start.sh
```

Linux systems may require the distribution's PortAudio package for low-latency preview. If the
`sounddevice` backend is unavailable, SonicDNA automatically attempts to use Qt Multimedia.

To install manually instead of using a launcher:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m sonicdna
```

On macOS or Linux, replace `.venv\Scripts\python` with `.venv/bin/python`.

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

## Command-line arguments

Supplying a query file and library folder to a launcher runs SonicDNA in command-line mode instead
of opening the desktop interface:

```text
sonicdna [--limit COUNT] [--database PATH] [--rebuild] QUERY LIBRARY
```

### Positional arguments

| Argument | Description |
| --- | --- |
| `QUERY` | Path to the audio sample used as the similarity query. |
| `LIBRARY` | Path to the library folder to scan recursively and search. |

### Options

| Option | Description |
| --- | --- |
| `-h`, `--help` | Display command-line help and exit. |
| `--limit COUNT` | Return at most this many ranked matches. The default is `10`. SonicDNA still examines the complete indexed library before returning the top results. |
| `--database PATH` | Use a custom SQLite index instead of the platform-default application-data location. |
| `--rebuild` | Discard cached vectors for the selected library and extract every supported file again. |

`--debug` is a Windows `start.bat` launcher mode rather than a SonicDNA CLI search argument. It
opens the desktop interface with an attached CMD window.

Windows example:

```powershell
.\start.bat "C:\Samples\query.wav" "D:\Drum Kits" --limit 25
```

PowerShell example with a custom index:

```powershell
.\start.ps1 "C:\Samples\query.wav" "D:\Drum Kits" --limit 50 --database "D:\Indexes\sonicdna.db"
```

macOS or Linux example:

```sh
./start.sh /samples/query.wav /samples/library --limit 25
```

Use `--rebuild` only when a complete re-extraction is needed. Normal searches already detect and
process new or modified files while reusing unchanged feature vectors.

## Desktop features

- Add and remove multiple recursively scanned library folders
- Drag one or more folders from the operating-system file manager into the Sample Libraries list
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

## Data storage and privacy

SonicDNA stores its persistent SQLite index outside the source-code directory in the current
user's platform-specific application-data location:

| Platform | Default index location |
| --- | --- |
| Windows | `%LOCALAPPDATA%\SonicDNA\index.db` |
| macOS | `~/Library/Application Support/SonicDNA/index.db` |
| Linux | `$XDG_DATA_HOME/SonicDNA/index.db`, or `~/.local/share/SonicDNA/index.db` when `XDG_DATA_HOME` is not set |

The index contains library-folder and sample paths, file metadata, extracted acoustic feature
vectors, and indexing-error records. It does not contain copies of the source audio.

Interface preferences are stored separately through Qt's native settings system. These include
window geometry, library-folder paths, similarity weights and custom presets, preview volume,
result count, and auto-play selection:

| Platform | Typical settings location |
| --- | --- |
| Windows | `HKEY_CURRENT_USER\Software\SonicDNA\SonicDNA` in the registry |
| macOS | `~/Library/Preferences/com.SonicDNA.SonicDNA.plist` |
| Linux | `$XDG_CONFIG_HOME/SonicDNA/SonicDNA.conf`, or `~/.config/SonicDNA/SonicDNA.conf` |

These data and settings locations are outside the repository and are not included in version
control, so another user receives an empty index and default settings. The exception is an
intentional CLI override such as `--database path/to/index.db`; avoid placing that custom database
inside the repository if it should remain private.

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

## Similarity weights

Open **Similarity Weights…** above the results list to control which acoustic characteristics
matter most when SonicDNA ranks matches. A higher value gives that characteristic more influence;
a lower value makes it less important. Setting a weight to `0.00` removes that characteristic
from the comparison.

| Weight | Default | Purpose |
| --- | ---: | --- |
| Body / Pitch | `0.90` | Prioritizes the dominant low-frequency peak and relative energy across bass and frequency bands. This is especially important for matching kicks with a similar fundamental body. |
| Attack | `0.85` | Compares how quickly the transient reaches its peak and the balance between the initial transient and the body. Increase it to favor similarly sharp or soft hits. |
| Decay | `0.70` | Compares how quickly the sound falls from its peak toward 50%, 20%, and 5% amplitude. Increase it to distinguish short, tight hits from longer tails. |
| Brightness | `0.50` | Uses spectral centroid, bandwidth, and rolloff to compare dark and bright samples. |
| Timbre | `0.70` | Compares MFCCs, mel-spectrum shape, and energy statistics. This captures the broader tone and spectral character of a sample. |
| Noise / Distortion | `0.45` | Uses spectral flatness and zero-crossing behavior to compare clean, noisy, distorted, or textured sounds. |
| Duration | `0.40` | Compares total analyzed sample length. Increase it when similarly timed one-shots are important. |

The defaults are tuned as a general kick-drum profile. Use **Reset Defaults** in the popup to
restore them. Accepted weights persist across application restarts.

The preset selector includes four built-in starting points:

- **Kick** emphasizes low-frequency body, pitch, and attack.
- **Snare** emphasizes attack, timbre, brightness, noise character, and decay.
- **Sub Bass** strongly emphasizes low-frequency body and sustained decay while reducing
  brightness and noise influence.
- **Hi-Hat** emphasizes brightness, attack, noise texture, and timbre while minimizing bass body.

Choose a profile and click **Load** to place its values into the sliders. Use **Save Current As…**
to store the current slider state under your own name. Custom presets persist across application
restarts and can be loaded or deleted from the same popup. Built-in profiles cannot be overwritten
or deleted.

The active preset name appears both in the popup and on the main **Similarity Weights** button.
Changing a slider adds `*` to the name (for example, `Snare*`) to indicate that the active values
have been modified from that preset.

Weights are applied to standardized feature vectors during search. Changing them does not alter
audio files or require re-indexing; run **Find Similar** again to apply the new ranking.

## Development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
```
