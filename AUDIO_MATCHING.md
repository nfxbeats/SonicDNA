# Audio Processing and Matching

This document describes the audio-analysis and similarity-search pipeline implemented by
SonicDNA. The matching is deterministic and local: source audio is decoded for analysis, but it
is never modified, uploaded, or copied into the index.

## Pipeline overview

For each search, SonicDNA performs these stages:

1. Recursively discover supported audio files in every selected Sample Library.
2. Extract and store a 177-value acoustic fingerprint for each new or changed file.
3. Extract the same fingerprint from the query sample.
4. Standardize each feature using the current set of indexed candidates.
5. Apply the selected similarity weights.
6. Calculate cosine similarity between the query and every candidate.
7. Sort all candidates from most to least similar and return the requested result count.

The result limit is applied only after every indexed candidate has been compared. It does not
stop library scanning or matching early.

## File discovery and incremental indexing

Library scanning is recursive. SonicDNA recognizes these extensions, case-insensitively:

- WAV (`.wav`)
- FLAC (`.flac`)
- AIFF (`.aiff` and `.aif`)
- Ogg Vorbis (`.ogg`)
- MP3 (`.mp3`)

Each indexed record includes the canonical file path, modification time, file size, feature
version, and the acoustic fingerprint. On later scans, a file is analyzed again only when its
modification time, size, or the application's feature version changes. Missing files are removed
from the index after a completed scan. A decoding or analysis failure is recorded and the scan
continues with the other files.

## Audio preprocessing

Every query and library sample goes through the same preprocessing:

1. `librosa` decodes the file.
2. Channels are mixed to mono.
3. Audio is resampled to 22,050 Hz.
4. The mean amplitude is subtracted to remove DC offset.
5. Leading and trailing silence are trimmed using a 50 dB threshold.
6. The waveform is peak-normalized to an absolute peak of 1.0.

Peak normalization means the matcher primarily compares acoustic shape, spectrum, envelope, and
duration rather than the original playback level. Empty, invalid, non-finite, or silent audio is
rejected. The source file remains unchanged.

The short-time Fourier transform uses an FFT size of up to 2,048 samples. For very short sounds,
SonicDNA uses the largest power of two that fits, with a minimum size of 32. The hop length is
one-quarter of the FFT size.

## The 177-value acoustic fingerprint

Many time-varying measurements are reduced to five statistics: mean, standard deviation, median,
10th percentile, and 90th percentile.

| Values | Feature group | What is measured |
| ---: | --- | --- |
| 100 | Timbre | Five statistics for each of 20 MFCC coefficients, representing broad spectral-envelope character. |
| 32 | Mel spectrum | Mean decibel energy in each of 32 mel-frequency bands. |
| 15 | Brightness | Five statistics each for spectral centroid, bandwidth, and rolloff. |
| 10 | Noise | Five statistics each for spectral flatness and zero-crossing rate. |
| 5 | Energy | Five statistics for RMS energy over time. |
| 2 | Attack | Time from the trimmed start to the absolute peak, plus the ratio of the first 30 ms of post-peak energy to the remaining body energy. |
| 3 | Decay | Time after the peak to first reach 50%, 20%, and 5% of peak amplitude. |
| 9 | Low-frequency body | Dominant frequency from 20–300 Hz, plus proportional energy in eight frequency bands from 20 Hz through the Nyquist limit. |
| 1 | Duration | Length in seconds after silence trimming. |

The eight body-energy bands are 20–40, 40–60, 60–90, 90–150, 150–300, 300–1,000,
1,000–5,000, and 5,000 Hz through the Nyquist limit. Band values are proportions of total spectral
power.

## Standardization

Raw feature units differ greatly: duration is measured in seconds, dominant pitch in hertz, and
band energy as proportions. Before matching, SonicDNA fits a `StandardScaler` independently to
each of the 177 dimensions across all candidates in the current search. It then transforms both
the candidates and query with those candidate-derived means and standard deviations:

```text
standardized value = (raw value - candidate mean) / candidate standard deviation
```

A dimension that is constant across the candidate set contributes no useful variation. Because
standardization depends on the candidate set, the same two files can receive a somewhat different
score when searched against a different collection of libraries.

## Similarity weights

The seven UI sliders expand across the fingerprint as follows:

| Slider | Fingerprint groups affected |
| --- | --- |
| Body / Pitch | Low-frequency body |
| Attack | Attack |
| Decay | Decay |
| Brightness | Brightness |
| Timbre | MFCC timbre, mel spectrum, and RMS energy |
| Noise / Distortion | Spectral flatness and zero-crossing rate |
| Duration | Trimmed duration |

Weights are clamped to the range 0.0–1.0 and multiply the corresponding standardized dimensions
for both the query and every candidate before cosine similarity is calculated. Consequently, a
zero weight removes that feature group from matching, while larger values increase its influence.
Because the weighted query and candidate are multiplied together in the cosine dot product, the
direct per-dimension contribution is proportional to the square of its slider weight.

The **Closest** preset sets every group to 1.0 and is the default. Instrument presets intentionally
reduce less relevant groups; they do not change how features are extracted or require rebuilding
the index. Weight changes apply on the next search.

## Distance, ranking, and displayed score

After standardization and weighting, SonicDNA calculates cosine similarity:

```text
cosine = dot(candidate, query) / (length(candidate) * length(query))
distance = 1 - cosine
displayed score = ((1 + cosine) / 2) * 100
```

The cosine is clipped to the mathematical range -1 through 1, and the displayed score is clipped
to 0–100. Results are sorted by ascending distance, which is equivalent to descending displayed
score. Rank 1 is therefore the closest match. The query file itself is excluded when its resolved
path exactly matches an indexed candidate.

The displayed value is a similarity score, not a statistical confidence, probability, or claim
that two sounds are perceptually identical. In this scale:

- 100 means the standardized, weighted vectors point in the same direction.
- 50 corresponds to orthogonal vectors.
- 0 means the vectors point in opposite directions.

Scores are most useful for comparing result order within the same search, candidate libraries,
and weight settings. They should not be treated as an absolute percentage of audible sameness
between unrelated searches.

## What matching does not use

The current fingerprint does not directly compare filenames, folder names, tags, musical-key
metadata, tempo metadata, stereo placement, or raw waveform samples. Mono conversion also means
stereo differences do not affect matching. The waveform images shown in the interface are visual
previews and are not the data used to calculate similarity.
