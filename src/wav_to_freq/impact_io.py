from __future__ import annotations

from dataclasses import dataclass 
from pathlib import Path
from typing import Literal, Sequence

import numpy as np
from scipy import signal
import soundfile as sf

from wav_to_freq.autodetect import AutoDetectInfo, auto_pick_hammer_channel
from wav_to_freq.signal_utils import as_f64, highpass, moving_mean, robust_sigma_mad
from wav_to_freq.enums import StereoChannel


# -------------------------
# Data containers
# -------------------------


@dataclass(frozen=True)
class StereoWav:
    """Raw stereo acquisition: hammer + response in the same WAV."""
    fs: float
    hammer: np.ndarray
    accel: np.ndarray
    path: Path
    autodetect: AutoDetectInfo | None = None
    hammer_channel: StereoChannel = StereoChannel.UNKNOWN


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


# -------------------------
# Low-level helpers
# -------------------------



def _validate_channel(ch: StereoChannel) -> None:
    if ch not in (StereoChannel.LEFT, StereoChannel.RIGHT):
        raise ValueError(f"hammer_channel must be 'left' or 'right'. Got {ch!r}")


# -------------------------
# Stage 0: read WAV
# -------------------------

def read_wav_stereo(path: str | Path) -> tuple[np.ndarray, np.ndarray, float, Path]:
    """
    Read a stereo wav and return (left, right, fs, Path).
    """
    p = Path(path)
    data, fs = sf.read(str(p), always_2d=True)
    if data.shape[1] != 2:
        raise ValueError(f"Expected stereo WAV (2 channels). Got shape={data.shape}")

    left = as_f64(data[:, 0])
    right = as_f64(data[:, 1])
    return left, right, float(fs), p


# -------------------------
# Stage 1: auto-pick hammer channel
# -------------------------


# -------------------------
# Stage 2: hit detection (on hammer channel only)
# -------------------------

def detect_hits(
    hammer: np.ndarray,
    fs: float,
    *,
    baseline_s: float = 2.0,
    threshold_sigma: float = 8.0,
    min_separation_s: float = 0.30,
    polarity: Literal["abs", "positive", "negative"] = "abs",
    min_abs_threshold: float | None = None,
    prominence_factor: float = 8.0,
    highpass_hz: float = 200.0,
    smooth_s: float = 0.003,
) -> tuple[np.ndarray, float]:
    """
    Detect hit indices from the hammer channel.

    Robust strategy:
      - high-pass to remove ringdown “bulk”
      - abs envelope (or polarity)
      - smooth a little
      - baseline MAD threshold + percentile fallback
      - prominence + min separation
    """
    hammer = as_f64(hammer)

    xhp = highpass(hammer, fs, fc_hz=highpass_hz)
    if polarity == "abs":
        y = np.abs(xhp)
    elif polarity == "positive":
        y = xhp
    else:
        y = -xhp

    y = moving_mean(y, int(max(1, round(smooth_s * fs))))

    # baseline noise estimate
    n0 = int(max(1000, min(y.size, round(baseline_s * fs))))
    base = y[:n0]

    sigma = robust_sigma_mad(base)
    thr_noise = float(np.median(base) + threshold_sigma * sigma)

    # percentile fallback (important when baseline is too quiet)
    if min_abs_threshold is None:
        p = float(np.percentile(y, 99.9))
        min_abs_threshold = 0.25 * p

    thr = max(thr_noise, float(min_abs_threshold))

    # prominence to reject small bumps
    prom = max(float(prominence_factor * sigma), 0.25 * thr)

    min_sep = int(max(1, round(min_separation_s * fs)))
    peaks, _ = signal.find_peaks(y, height=thr, distance=min_sep, prominence=prom)
    return peaks.astype(int, copy=False), thr


# -------------------------
# Stage 3: map to StereoWav + extract windows
# -------------------------

def load_stereo_wav(
    path: str | Path,
    *,
    hammer_channel: StereoChannel,
) -> StereoWav:
    """
    Load a stereo WAV and return hammer + accel channels.

    If hammer_channel is None:
      pick hammer via an impulsiveness score designed for:
        - small sharp hammer spikes
        - larger long response ringdown
    """
    left, right, fs, p = read_wav_stereo(path)

    autodetect: AutoDetectInfo| None = None

    if hammer_channel is StereoChannel.UNKNOWN:
        picked, score_left, score_right = auto_pick_hammer_channel(left, right, fs)
        hammer_channel = picked
        autodetect= AutoDetectInfo(
            method="kurtosis_hp200",
            score_left = score_left,
            score_right=score_right,
            picked=picked
        )
    else:
        _validate_channel(hammer_channel)

    if hammer_channel == "left":
        hammer, accel = left, right
    else:
        hammer, accel = right, left

    return StereoWav(
        fs=fs,
        hammer=hammer,
        accel=accel,
        hammer_channel=hammer_channel,
        path=p,
        autodetect=autodetect
    )


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
    fs = float(stereo.fs)
    n_pre = int(round(pre_s * fs))
    n_post = int(round(post_s * fs))

    out: list[HitWindow] = []
    for idx in hit_indices:
        idx = int(idx)
        i0 = idx - n_pre
        i1 = idx + n_post
        if i0 < 0 or i1 > stereo.hammer.size:
            continue
        out.append(
            HitWindow(
                hit_index=idx,
                t0=float(idx / fs),
                hammer=stereo.hammer[i0:i1].copy(),
                accel=stereo.accel[i0:i1].copy(),
            )
        )
    return out


def prepare_hits(
    wav_path: str | Path,
    *,
    hammer_channel: StereoChannel = StereoChannel.UNKNOWN,
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
      - load stereo WAV (auto or forced channel)
      - detect hits (on hammer)
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

