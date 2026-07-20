"""Deterministic audio preprocessing and feature extraction."""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

from sonicdna.feature_schema import FEATURE_VECTOR_LENGTH, validate_schema

ANALYSIS_SAMPLE_RATE = 22_050
SUPPORTED_EXTENSIONS = {".wav", ".flac", ".aiff", ".aif", ".ogg", ".mp3"}


def _stats(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    return np.asarray(
        [np.mean(values), np.std(values), np.median(values),
         np.percentile(values, 10), np.percentile(values, 90)],
        dtype=np.float32,
    )


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    """Load, normalize, and trim a sample without modifying its source file."""
    audio, sample_rate = librosa.load(path, sr=ANALYSIS_SAMPLE_RATE, mono=True)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0 or not np.all(np.isfinite(audio)):
        raise ValueError("decoded audio is empty or invalid")
    audio -= np.mean(audio)
    audio, _ = librosa.effects.trim(audio, top_db=50)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak <= np.finfo(np.float32).eps:
        raise ValueError("audio is silent after preprocessing")
    return audio / peak, sample_rate


def extract_features(path: Path) -> np.ndarray:
    """Extract the Version 1 fixed-length acoustic fingerprint."""
    validate_schema()
    audio, sr = load_audio(path)
    n_fft = min(2048, max(32, 2 ** int(np.floor(np.log2(max(32, audio.size))))))
    hop = max(1, n_fft // 4)
    spectrum = np.abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop))
    power = spectrum**2

    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=20, n_fft=n_fft, hop_length=hop)
    mel = librosa.feature.melspectrogram(
        y=audio, sr=sr, n_fft=n_fft, hop_length=hop, n_mels=32
    )
    centroid = librosa.feature.spectral_centroid(S=power, sr=sr)
    bandwidth = librosa.feature.spectral_bandwidth(S=power, sr=sr)
    rolloff = librosa.feature.spectral_rolloff(S=power, sr=sr)
    flatness = librosa.feature.spectral_flatness(S=power)
    zcr = librosa.feature.zero_crossing_rate(audio, frame_length=n_fft, hop_length=hop)
    rms = librosa.feature.rms(S=spectrum, frame_length=n_fft, hop_length=hop)

    envelope = np.abs(audio)
    peak_index = int(np.argmax(envelope))
    peak = float(envelope[peak_index])
    attack = peak_index / sr

    def decay_time(ratio: float) -> float:
        below = np.flatnonzero(envelope[peak_index:] <= peak * ratio)
        return float(below[0] / sr) if below.size else float((audio.size - peak_index) / sr)

    transient_end = min(audio.size, peak_index + int(0.03 * sr))
    transient_energy = float(np.sum(audio[peak_index:transient_end] ** 2))
    body_energy = float(np.sum(audio[transient_end:] ** 2))
    transient_ratio = transient_energy / max(body_energy, 1e-12)

    frequencies = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    mean_power = np.mean(power, axis=1)
    low_mask = (frequencies >= 20) & (frequencies <= 300)
    dominant = float(frequencies[low_mask][np.argmax(mean_power[low_mask])]) if low_mask.any() else 0.0
    bands = [(20, 40), (40, 60), (60, 90), (90, 150), (150, 300),
             (300, 1000), (1000, 5000), (5000, sr / 2 + 1)]
    total = max(float(np.sum(mean_power)), 1e-12)
    band_energy = [float(np.sum(mean_power[(frequencies >= lo) & (frequencies < hi)]) / total)
                   for lo, hi in bands]

    vector = np.concatenate([
        *(_stats(row) for row in mfcc),
        np.mean(librosa.power_to_db(mel + 1e-12), axis=1),
        _stats(centroid), _stats(bandwidth), _stats(rolloff),
        _stats(flatness), _stats(zcr), _stats(rms),
        np.asarray([attack, transient_ratio], dtype=np.float32),
        np.asarray([decay_time(0.5), decay_time(0.2), decay_time(0.05)], dtype=np.float32),
        np.asarray([dominant, *band_energy], dtype=np.float32),
        np.asarray([audio.size / sr], dtype=np.float32),
    ]).astype(np.float32)
    if vector.shape != (FEATURE_VECTOR_LENGTH,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"invalid feature vector: shape={vector.shape}")
    return vector

