from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

import numpy as np
import soundfile as sf
from scipy import signal


Channel = Literal["left", "right"]


@dataclass(frozen=True)
class StereoWav:
    """Raw stereo acquisition: hammer + response in the same WAV."""
    fs: float
    hammer: np.ndarray
    accel: np.ndarray
    hammer_channel: Channel
    path: Path


@dataclass(frozen=True)
class HitWindow:
    """One extracted hit window, aligned on the detected impact peak."""
    hit_index: int          # sample index in the full signal
    t0: float               # seconds (hit_index / fs)
    hammer: np.ndarray      # windowed hammer samples
    accel: np.ndarray       # windowed accel samples


@dataclass(frozen=True)
class HitDetectionReport:
    n_hits_found: int
    n_hits_used: int
    threshold: float
    min_separation_s: float
    pre_s: float
    post_s: float


def load_stereo_wav(
    path: str | Path,
    *,
    hammer_channel: Channel | None = None,
) -> StereoWav:
    """
    Load a stereo WAV and return hammer + accel channels.

    If hammer_channel=None, a heuristic is used:
    - hammer tends to be more 'impulsive' (higher kurtosis / peakiness).
    """
    p = Path(path)
    data, fs = sf.read(str(p), always_2d=True)
    if data.shape[1] != 2:
        raise ValueError(f"Expected stereo WAV (2 channels). Got shape={data.shape}")

    left = data[:, 0].astype(np.float64, copy=False)
    right = data[:, 1].astype(np.float64, copy=False)

    if hammer_channel is None:
        # Simple "impulsiveness" score: peak / RMS (higher for hammer spikes)
        def impulsiveness(x: np.ndarray) -> float:
            rms = float(np.sqrt(np.mean(x * x)) + 1e-30)
            pk = float(np.max(np.abs(x)) + 1e-30)
            return pk / rms

        score_l = impulsiveness(left)
        score_r = impulsiveness(right)
        hammer_channel = "left" if score_l >= score_r else "right"

    if hammer_channel == "left":
        hammer, accel = left, right
    else:
        hammer, accel = right, left

    return StereoWav(fs=fs, hammer=hammer, accel=accel, hammer_channel=hammer_channel, path=p)


def _robust_sigma_mad(x: np.ndarray) -> float:
    """Robust sigma estimate based on MAD."""
    med = np.median(x)
    mad = np.median(np.abs(x - med)) + 1e-30
    return 1.4826 * mad


def detect_hits(
    hammer: np.ndarray,
    fs: float,
    *,
    baseline_s: float = 2.0,
    threshold_sigma: float = 8.0,
    min_separation_s: float = 0.30,
    polarity: Literal["abs", "positive", "negative"] = "abs",
    # new:
    min_abs_threshold: float | None = None,
    prominence_factor: float = 8.0,
) -> tuple[np.ndarray, float]:
    """
    Detect hit indices from the hammer channel.

    Robust strategy:
    1) Compute a noise-based threshold from baseline (MAD).
    2) If baseline is (near) silent -> fallback to a percentile-based absolute threshold.
    3) Require prominence to reject tiny peaks.
    """
    hammer = np.asarray(hammer, dtype=np.float64)

    # choose signal polarity
    if polarity == "abs":
        y = np.abs(hammer)
    elif polarity == "positive":
        y = hammer
    else:
        y = -hammer

    # baseline noise estimate
    n0 = max(1000, int(round(baseline_s * fs)))
    n0 = min(n0, len(y))
    base = y[:n0]

    sigma = _robust_sigma_mad(base)  # already >0 protected by +1e-30 in helper
    thr_noise = float(np.median(base) + threshold_sigma * sigma)

    # fallback: if sigma ~ 0 (digital silence), use signal percentile
    if min_abs_threshold is None:
        # "typical big values" without being the absolute max
        p = float(np.percentile(y, 99.9))
        min_abs_threshold = 0.25 * p  # adjustable, but works well for your hammer spikes

    thr = max(thr_noise, float(min_abs_threshold))

    # prominence (reject small bumps)
    prom = max(float(prominence_factor * sigma), 0.25 * thr)

    min_sep = int(round(min_separation_s * fs))
    peaks, _ = signal.find_peaks(y, height=thr, distance=min_sep, prominence=prom)

    return peaks.astype(int, copy=False), thr


def extract_hit_windows(
    stereo: StereoWav,
    hit_indices: Sequence[int],
    *,
    pre_s: float = 0.05,
    post_s: float = 1.50,
) -> list[HitWindow]:
    """
    Extract time windows around each hit index.
    Windows are clipped if they exceed signal bounds (those hits are dropped).
    """
    fs = stereo.fs
    n_pre = int(round(pre_s * fs))
    n_post = int(round(post_s * fs))

    out: list[HitWindow] = []
    for idx in hit_indices:
        i0 = idx - n_pre
        i1 = idx + n_post
        if i0 < 0 or i1 > len(stereo.hammer):
            continue
        out.append(
            HitWindow(
                hit_index=int(idx),
                t0=float(idx / fs),
                hammer=stereo.hammer[i0:i1].copy(),
                accel=stereo.accel[i0:i1].copy(),
            )
        )
    return out


def prepare_hits(
    wav_path: str | Path,
    *,
    hammer_channel: Channel | None = None,
    # detection params
    baseline_s: float = 2.0,
    threshold_sigma: float = 8.0,
    min_separation_s: float = 0.30,
    polarity: Literal["abs", "positive", "negative"] = "abs",
    # window params
    pre_s: float = 0.05,
    post_s: float = 1.50,
) -> tuple[StereoWav, list[HitWindow], HitDetectionReport]:
    """
    One-call convenience wrapper:
    - load stereo WAV
    - detect hits
    - extract per-hit windows
    """
    stereo = load_stereo_wav(wav_path, hammer_channel=hammer_channel)
    hit_idx, thr = detect_hits(
        stereo.hammer,
        stereo.fs,
        baseline_s=baseline_s,
        threshold_sigma=threshold_sigma,
        min_separation_s=min_separation_s,
        polarity=polarity,
    )
    windows = extract_hit_windows(stereo, hit_idx, pre_s=pre_s, post_s=post_s)

    report = HitDetectionReport(
        n_hits_found=int(len(hit_idx)),
        n_hits_used=int(len(windows)),
        threshold=float(thr),
        min_separation_s=float(min_separation_s),
        pre_s=float(pre_s),
        post_s=float(post_s),
    )
    return stereo, windows, report

