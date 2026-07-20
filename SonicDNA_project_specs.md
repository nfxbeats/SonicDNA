# Project Specification: SonicDNA

## 1. Project Overview

Build SonicDNA, a cross-platform desktop application that searches a user's local audio sample library for files that sound similar to a selected one-shot sample.

The initial target use case is drum one-shots, especially kick drums, but the architecture should support snares, claps, hi-hats, percussion, bass hits, and other short audio samples later.

The application must run locally on Windows, macOS, and Linux. It must not require cloud processing or an internet connection for normal use.

The initial implementation should use Python and PySide6.

---

## 2. Product Identity

**Product name:** SonicDNA

**Working description:** A local-first audio similarity search application for finding samples with matching acoustic characteristics.

**Primary positioning:** SonicDNA analyzes the measurable characteristics of audio samples—such as timbre, spectral balance, low-frequency body, attack, decay, brightness, and noise content—and uses those characteristics as a searchable acoustic fingerprint.

**Suggested tagline:**

```text
Find the sound in your sound.
```

The application name should be displayed as `SonicDNA` in all user-facing interfaces. Internal Python package names, configuration directories, and identifiers should use `sonicdna` where lowercase naming is required.

---

## 3. Primary Goal

Allow a user to:

1. Select one or more local sample-library folders.
2. Scan and index supported audio files.
3. Select or drag in a query sample.
4. Search the local index for acoustically similar samples.
5. Audition and compare the returned results.
6. Reveal, copy, or drag matched files into another application such as a DAW.

The system should prioritize perceptual similarity rather than filename similarity.

---

## 4. Initial Scope

### Included in Version 1

- Cross-platform desktop UI
- Local recursive folder scanning
- Audio metadata extraction
- Audio feature extraction
- Persistent SQLite index
- Incremental rescanning
- Query-by-example similarity search
- Ranked results
- Audio preview
- Waveform display
- Adjustable similarity weights
- Drag-and-drop query loading
- Result sorting and filtering
- Reveal file in operating-system file manager
- Copy file path
- Open file with default application
- Export results to CSV
- User settings persistence   
- Basic error logging

### Excluded from Version 1
  
- Cloud synchronization
- User accounts
- Online sample stores
- Automatic sample downloading
- Audio editing
- DAW plugin formats such as VST3, AU, or AAX
- Real-time recording from a microphone
- Full-loop tempo matching
- Automatic genre tagging
- Neural-network training
- Multi-user support
- Remote libraries
- Duplicate-file deletion
- Automatic file reorganization
- Metadata writing into source audio files

These may be added later, but Version 1 should not depend on them.

---

## 5. Technology Stack

### Required

- Python 3.12 or newer
- PySide6
- NumPy
- SciPy
- librosa
- soundfile
- scikit-learn
- SQLite
- PyInstaller
- pytest

### Recommended

- sounddevice for low-latency preview
- platformdirs for application-data paths
- mutagen for additional metadata support
- ruff for linting
- mypy for static type checking
- loguru or standard Python logging
- joblib for model/index serialization where appropriate

### Optional Future Dependencies

- FAISS for very large libraries
- CLAP or another audio-embedding model
- ONNX Runtime for local neural inference
- watchdog for filesystem change monitoring

---

## 6. Cross-Platform Requirements

The application must support:

- Windows 10 and Windows 11
- Current supported macOS releases
- Common modern Linux desktop distributions

The source code should remain platform-neutral where practical.

Platform-specific behavior must be isolated behind helper functions, especially:

- Reveal in Explorer
- Reveal in Finder
- Reveal in Linux file manager
- Open file with default application
- Drag files out of the application
- Application-data folder discovery
- Path normalization

Do not hard-code Windows drive letters, path separators, or registry dependencies.

Use `pathlib.Path` for filesystem operations.

---

## 7. Core User Workflow

### First Run

1. User launches the application.
2. Application displays an empty-library state.
3. User clicks **Add Library Folder**.
4. User selects a folder.
5. Application recursively scans supported files.
6. Application extracts metadata and acoustic features.
7. Progress is displayed without freezing the UI.
8. Index is saved locally.
9. User selects or drops a query sample.
10. User clicks **Find Similar**.
11. Ranked matches appear.
12. User auditions results and uses the desired file.

### Later Runs

1. Application loads the existing database.
2. Library folders are restored.
3. Application optionally checks for changed files.
4. Existing indexed files remain immediately searchable.
5. Only new, modified, moved, or missing files are updated.

---

## 8. Supported Audio Formats

Initial supported extensions:

- `.wav`
- `.flac`
- `.aiff`
- `.aif`
- `.ogg`
- `.mp3`

The application should skip unsupported or unreadable files and continue scanning.

Each skipped file must be logged with:

- Path
- Error type
- Error message
- Date and time

The UI should show a non-blocking scan summary rather than interrupting the scan for each bad file.

---

## 9. Audio Preprocessing

Each sample should be processed consistently before feature extraction.

Required preprocessing steps:

1. Load audio.
2. Convert to mono.
3. Resample to a fixed analysis sample rate.
4. Remove DC offset.
5. Trim leading and trailing near-silence.
6. Peak normalize for analysis only.
7. Preserve original file unchanged.
8. Reject empty or invalid decoded audio.
9. Handle very short samples safely.

Recommended analysis sample rate:

```text
22050 Hz
```

Recommended silence trim:

```text
top_db = 50
```

Do not write processed audio back to the source file.

---

## 10. Feature Extraction

Each file must be converted into a fixed-length numeric feature vector.

### 9.1 General Timbre Features

Include:

- MFCC summary statistics
- Mel-spectrogram band averages
- Spectral centroid
- Spectral bandwidth
- Spectral rolloff
- Spectral flatness
- Zero-crossing rate
- RMS energy statistics

For time-varying features, calculate summary values such as:

- Mean
- Standard deviation
- Median
- 10th percentile
- 90th percentile

### 9.2 Drum-Specific Features

Include:

- Total duration
- Estimated attack time
- Time from peak to 50% amplitude
- Time from peak to 20% amplitude
- Time from peak to 5% amplitude
- Transient-to-body energy ratio
- Dominant low-frequency peak
- Relative energy in frequency bands

Suggested frequency bands:

```text
20-40 Hz
40-60 Hz
60-90 Hz
90-150 Hz
150-300 Hz
300-1000 Hz
1000-5000 Hz
5000 Hz-Nyquist
```

### 9.3 Feature Groups

Features must be grouped logically so they can be weighted independently.

Required groups:

- Timbre
- Mel spectrum
- Low-frequency body
- Attack
- Decay
- Brightness
- Noise/distortion
- Duration

Do not implement the feature vector as an undocumented flat list. Maintain a stable feature schema.

Example:

```python
FEATURE_SCHEMA = {
    "timbre": (0, 100),
    "mel_spectrum": (100, 132),
    "brightness": (132, 147),
    "noise": (147, 157),
    "envelope": (157, 163),
    "frequency_bands": (163, 172),
}
```

The exact offsets may differ, but they must be deterministic and versioned.

---

## 11. Similarity Search

### 10.1 Search Method

Version 1 should use nearest-neighbor search over standardized feature vectors.

Required steps:

1. Load indexed vectors.
2. Standardize features using statistics derived from the indexed library.
3. Apply user-defined feature-group weights.
4. Compare the query vector to library vectors.
5. Rank results by distance.
6. Return the top N matches.

Default distance metric:

```text
Cosine distance
```

Alternative metrics may be made configurable later.

### 10.2 Similarity Score

Convert raw distance into a display score between 0 and 100.

The UI must label the value as a relative similarity score, not a scientific probability.

Example:

```text
Similarity: 93.4
```

Do not display a percent sign unless the score mapping is explicitly normalized and documented.

### 10.3 Query Exclusion

If the query file exists in the indexed library, exclude the exact same file from the results by default.

Optionally allow the user to include it.

### 10.4 Weighting

Provide adjustable weights for:

- Body/Pitch
- Attack
- Decay
- Brightness
- Timbre
- Noise/Distortion
- Duration

Default profile for kick drums:

```text
Body/Pitch: 0.90
Attack: 0.85
Decay: 0.70
Brightness: 0.50
Timbre: 0.70
Noise/Distortion: 0.45
Duration: 0.40
```

Weights must be persisted.

Provide a **Reset Defaults** action.

---

## 12. Persistent Index

Use SQLite for persistent storage.

### 11.1 Database Location

Store the database in the platform-appropriate application-data directory.

Use `platformdirs`.

Example logical name:

```text
SonicDNA/index.db
```

### 11.2 Required Tables

#### `library_folders`

```sql
CREATE TABLE library_folders (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    added_at TEXT NOT NULL,
    last_scan_at TEXT
);
```

#### `samples`

```sql
CREATE TABLE samples (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    library_folder_id INTEGER,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    modified_ns INTEGER NOT NULL,
    size_bytes INTEGER NOT NULL,
    duration_seconds REAL,
    sample_rate INTEGER,
    channels INTEGER,
    feature_version INTEGER NOT NULL,
    feature_vector BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (library_folder_id)
        REFERENCES library_folders(id)
        ON DELETE SET NULL
);
```

#### `app_metadata`

```sql
CREATE TABLE app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

### 11.3 Recommended Indexes

```sql
CREATE INDEX idx_samples_path
ON samples(path);

CREATE INDEX idx_samples_folder
ON samples(library_folder_id);

CREATE INDEX idx_samples_modified
ON samples(modified_ns);
```

### 11.4 Feature Storage

Store vectors as little-endian `float32` byte arrays.

Example:

```python
blob = vector.astype("<f4").tobytes()
```

Restore using:

```python
vector = np.frombuffer(blob, dtype="<f4")
```

Validate vector length against the current feature schema.

---

## 13. Incremental Scanning

A full rescan should not reprocess unchanged files.

Use at least:

- Canonical path
- File size
- Modification timestamp
- Feature version

Reprocess a file when:

- It is new.
- Its size changed.
- Its modification timestamp changed.
- The feature extraction version changed.
- The previous extraction failed and the user retries.

Remove or mark missing files when they no longer exist.

The UI should offer:

- Scan All
- Scan Selected Folder
- Rescan Changed Files
- Rebuild Entire Index
- Remove Missing Files

A full rebuild must require confirmation.

---

## 14. Main Window Layout

The main window should contain four primary regions.

### 13.1 Library Section

Controls:

- Library folder list
- Add folder
- Remove folder
- Enable/disable folder
- Scan/update
- Rebuild index
- Progress bar
- Scan status text

Display:

- Indexed file count
- Failed file count
- Last scan time
- Database location

### 13.2 Query Section

Controls:

- Query path
- Browse button
- Drag-and-drop target
- Play
- Stop
- Clear
- Find Similar

Display:

- Waveform
- Filename
- Duration
- Sample rate
- Channels
- File type

### 13.3 Similarity Controls

Controls:

- Weight sliders
- Result count
- Minimum score filter
- Drum profile preset
- Reset defaults

Initial result-count options:

```text
10
25
50
100
```

### 13.4 Results Section

Use a sortable table.

Required columns:

- Rank
- Similarity
- Play button or state
- Filename
- Duration
- Dominant frequency
- File type
- Parent folder
- Full path

Optional columns:

- Attack
- Decay
- Brightness
- Indexed date

---

## 15. Result Interactions

The user must be able to:

- Single-click to select
- Double-click to play
- Press Space to play or stop
- Use Up and Down arrows to move through results
- Automatically audition the selected result if enabled
- Right-click for context menu
- Reveal in file manager
- Open with default application
- Copy full path
- Copy filename
- Export selected result
- Export all results to CSV
- Drag a file out of the application

Dragging a result should expose the original local file path using Qt MIME URLs so compatible DAWs can accept it.

Do not duplicate or move source files unless the user explicitly chooses an export/copy operation.

---

## 16. Audio Playback

Playback must support rapid one-shot auditioning.

Required behavior:

- Stop the currently playing sample when another starts.
- Restart from the beginning when replayed.
- Support keyboard audition.
- Avoid blocking the UI.
- Provide a volume control.
- Persist preview volume.
- Handle missing files gracefully.
- Show currently playing row.

Preferred implementation:

```text
sounddevice + soundfile
```

Fallback:

```text
Qt Multimedia
```

The playback layer must be abstracted so the backend can be changed later.

Suggested interface:

```python
class AudioPlayer(Protocol):
    def play(self, path: Path) -> None: ...
    def stop(self) -> None: ...
    def set_volume(self, value: float) -> None: ...
    def is_playing(self) -> bool: ...
```

---

## 17. Waveform Display

Display a simplified waveform for the query and optionally for selected results.

Requirements:

- Downsample waveform points for display.
- Do not render millions of raw samples.
- Handle mono and stereo files.
- Scale waveform to widget bounds.
- Indicate playhead if practical.
- Repaint efficiently.
- Cache preview waveform data.

Waveform generation must not block the UI for large files.

---

## 18. Threading and Responsiveness

The UI thread must never perform:

- Recursive scanning
- Audio decoding
- Feature extraction
- Full database loading
- Large nearest-neighbor calculations
- CSV export for large result sets

Use Qt workers, `QThread`, or a controlled thread pool.

Workers must report:

- Current file
- Files processed
- Total files
- Percentage
- Errors
- Completion
- Cancellation

The user must be able to cancel a long scan.

Cancellation should stop after the current file is safely processed and leave the database valid.

Database writes should use transactions and batching.

---

## 19. Application Settings

Persist settings using `QSettings` or a small local configuration file.

Required settings:

- Window position and size
- Last query folder
- Library folders
- Result count
- Similarity weights
- Preview volume
- Auto-audition enabled
- Include query file in results
- Minimum score
- Visible result columns
- Last export folder

Do not store sensitive information.

---

## 20. Project Structure

Use a modular structure similar to:

```text
sonicdna/
├── pyproject.toml
├── README.md
├── PROJECT_SPECS.md
├── main.py
├── sonicdna/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── logging_config.py
│   ├── models/
│   │   ├── sample.py
│   │   ├── search_result.py
│   │   └── settings.py
│   ├── audio/
│   │   ├── loader.py
│   │   ├── preprocessing.py
│   │   ├── features.py
│   │   ├── feature_schema.py
│   │   ├── playback.py
│   │   └── waveform.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── migrations.py
│   │   ├── repositories.py
│   │   └── schema.sql
│   ├── indexing/
│   │   ├── scanner.py
│   │   ├── indexer.py
│   │   └── change_detector.py
│   ├── search/
│   │   ├── engine.py
│   │   ├── scaler.py
│   │   ├── weighting.py
│   │   └── scoring.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── results_model.py
│   │   ├── waveform_widget.py
│   │   ├── library_panel.py
│   │   ├── query_panel.py
│   │   ├── settings_dialog.py
│   │   └── resources/
│   ├── workers/
│   │   ├── scan_worker.py
│   │   ├── search_worker.py
│   │   └── waveform_worker.py
│   └── platform/
│       ├── file_actions.py
│       └── paths.py
└── tests/
    ├── test_features.py
    ├── test_database.py
    ├── test_scanner.py
    ├── test_search.py
    ├── test_weighting.py
    └── fixtures/
```

Avoid putting all logic in `main.py` or the main-window class.

---

## 21. Data Models

Use dataclasses or typed model classes.

Example:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SampleRecord:
    id: int | None
    path: Path
    filename: str
    extension: str
    modified_ns: int
    size_bytes: int
    duration_seconds: float
    sample_rate: int
    channels: int
    feature_version: int
```

Search result:

```python
@dataclass(slots=True)
class SearchResult:
    sample: SampleRecord
    similarity_score: float
    raw_distance: float
    dominant_frequency: float | None = None
```

---

## 22. Logging

Use rotating log files.

Log location must use the platform-specific application-data or log directory.

Log:

- Application startup
- Application version
- Python version
- Operating system
- Database migration activity
- Scan start and finish
- File extraction failures
- Search failures
- Playback failures
- Unhandled exceptions

Do not log raw audio data.

The UI should include an **Open Log Folder** action.

---

## 23. Error Handling

The application must continue operating when possible.

Examples:

- One corrupt file must not stop a library scan.
- One missing result file must not crash playback.
- A locked database should show a clear error.
- A failed migration should preserve the previous database where possible.
- An unsupported codec should be logged and skipped.
- A removed library folder should not crash startup.
- A canceled scan should leave committed records intact.

Use user-facing messages that explain the action the user can take.

Avoid showing raw tracebacks in normal dialogs.

---

## 24. Testing Requirements

### Unit Tests

Cover:

- Audio preprocessing
- Feature vector length
- Feature vector determinism
- Silent-file handling
- Very-short-file handling
- Feature schema validation
- SQLite serialization/deserialization
- Incremental-change detection
- Weight application
- Distance-to-score conversion
- Query exclusion
- Missing-file handling

### Integration Tests

Cover:

- Indexing a small fixture library
- Updating changed files
- Removing missing files
- Searching and returning deterministic nearest results
- Exporting CSV
- Loading persisted settings

### UI Smoke Tests

At minimum:

- Main window launches
- Folder can be added
- Query can be selected
- Search can be started
- Result table populates
- Playback controls do not crash
- Long-running scan does not block the event loop

Use synthetic test audio where possible to avoid licensing issues.

---

## 25. Performance Targets

These are engineering targets, not strict guarantees.

### Initial Scan

For short WAV one-shots on a typical desktop:

```text
At least 10-30 files per second where storage and decoding permit
```

Performance will vary by format and hardware.

### Search

For an already loaded index of 100,000 samples:

```text
Target under 1 second
```

For smaller libraries:

```text
Target under 250 ms
```

### Memory

Do not load decoded audio for the entire library into memory.

Only load:

- Metadata
- Feature vectors
- Current query
- Current preview file
- Cached waveform previews

Use `float32` vectors.

---

## 26. Packaging

Use PyInstaller for initial desktop builds.

Build separately on each target operating system.

Expected artifacts:

```text
Windows: SonicDNA.exe
macOS: SonicDNA.app
Linux: SonicDNA
```

Provide:

- Application icon
- Version metadata
- Non-console/windowed build
- Included schema and migration resources
- Included licenses for third-party dependencies

Do not assume one build artifact will run on all platforms.

---

## 27. Versioning

Use semantic versioning.

Example:

```text
0.1.0
```

Maintain separate version constants for:

- Application version
- Database schema version
- Feature extraction version

A feature-version change must trigger re-indexing of incompatible vectors.

A database migration must not silently destroy the existing database.

---

## 28. Security and Privacy

The application is local-first.

Requirements:

- Do not upload filenames or audio.
- Do not make network requests during normal operation.
- Do not modify original audio files.
- Do not execute scanned files.
- Treat filenames and metadata as untrusted text.
- Use parameterized SQL queries.
- Validate drag-and-drop URLs.
- Resolve paths carefully.
- Avoid shell command construction from raw paths.

Any future online feature must be explicitly opt-in.

---

## 29. Development Phases

### Phase 1: Core Search Engine

Implement:

- Audio loading
- Preprocessing
- Feature extraction
- Feature schema
- In-memory nearest-neighbor search
- Command-line test harness

Deliverable:

```text
A CLI that accepts a query sample and a folder and prints ranked matches.
```

### Phase 2: Persistent Index

Implement:

- SQLite schema
- Folder scanning
- Incremental indexing
- Feature serialization
- Index loading
- Rebuild support

Deliverable:

```text
A CLI that builds and updates an index without recomputing unchanged files.
```

### Phase 3: Basic Desktop UI

Implement:

- Main window
- Folder management
- Query selection
- Scan progress
- Search
- Results table
- Basic playback

Deliverable:

```text
A functional desktop application with no advanced styling requirement.
```

### Phase 4: Workflow Improvements

Implement:

- Drag-and-drop query
- Drag result into DAW
- Waveform
- Keyboard audition
- Context menu
- CSV export
- Weight sliders
- Settings persistence

### Phase 5: Packaging and Quality

Implement:

- Tests
- Logging
- Error dialogs
- Cross-platform file actions
- PyInstaller builds
- Documentation
- Release checklist

---

## 30. Acceptance Criteria

Version 1 is complete when all of the following are true:

1. The application launches on Windows, macOS, and Linux from packaged builds.
2. A user can add a local sample-library folder.
3. The application recursively indexes supported audio files.
4. The UI remains responsive during scanning.
5. A scan can be canceled safely.
6. The index persists after restart.
7. Unchanged files are not reprocessed during an incremental scan.
8. A user can select or drop a query sample.
9. The application returns ranked acoustically similar results.
10. The query file is excluded by default when present in the library.
11. The user can adjust similarity weights.
12. The user can audition the query and results.
13. The user can reveal a result in the system file manager.
14. The user can copy a result path.
15. The user can drag a result file out of the application.
16. The user can export results to CSV.
17. Corrupt or unsupported files do not terminate a scan.
18. Original source audio files are never modified.
19. Tests cover the core extraction, indexing, and search behavior.
20. The project contains build and development instructions.

---

## 31. Coding Standards

- Use Python type hints throughout.
- Prefer `pathlib.Path`.
- Use dataclasses for simple records.
- Keep UI and business logic separate.
- Keep database access behind repository classes.
- Keep platform-specific code isolated.
- Use clear docstrings for public functions and classes.
- Avoid global mutable state.
- Avoid broad `except Exception` unless errors are logged and safely contained.
- Use parameterized SQL.
- Use transactions for batch writes.
- Keep functions focused and testable.
- Use Ruff formatting/linting rules.
- Use pytest.
- Do not generate placeholder methods that silently pass.
- Do not swallow errors without logging.

---

## 32. Initial Codex Instructions

When implementing this project:

1. Start with Phase 1.
2. Create the project structure and `pyproject.toml`.
3. Implement a working CLI before building the UI.
4. Write tests with each subsystem.
5. Keep the feature schema explicit and versioned.
6. Do not add neural embeddings in the first implementation.
7. Do not add cloud services.
8. Do not add unnecessary frameworks.
9. Prefer a working, testable implementation over premature optimization.
10. After each phase, update `README.md` with run and test instructions.
11. Keep all platform-specific operations behind a small adapter module.
12. Use synthetic audio fixtures for tests.
13. Ensure all long-running operations can later be moved into Qt worker threads.
14. Do not tightly couple the search engine to PySide6.
15. Preserve compatibility with a future CLI, GUI, or API frontend.

---

## 33. Future Enhancements

Possible later additions:

- Sample type classifier
- Kick, snare, clap, hat, and percussion presets
- Neural audio embeddings
- Hybrid DSP and embedding scoring
- Duplicate detection
- Near-duplicate clustering
- Folder watch mode
- Favorites
- User ratings
- “More like this” feedback
- Search history
- Spectrogram display
- Batch query mode
- Compare two selected samples
- Similarity explanation by feature group
- Key or pitch filtering
- BPM-aware loop search
- VST3 or CLAP plugin companion
- Local REST API
- DAW integration helpers
- FAISS index for very large libraries
- Optional GPU acceleration

These should not complicate the initial implementation.
