from pathlib import Path
from typing import Literal, Sequence
import numpy as np

from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.domain.types import HitDetectionReport, HitWindow, StereoWav
from wav_to_freq.dsp.filters import highpass
from wav_to_freq.dsp.stats import as_f64, moving_mean, robust_sigma_mad

from scipy import signal

from wav_to_freq.io.wav_reader import load_stereo_wav

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
    pre_n = int(round(pre_s * fs))
    post_n = int(round(post_s * fs))
    n_samples = len(stereo.hammer)

    hit_id: int = 0

    windows: list[HitWindow] = []
    for hit_index in hit_indices:

        hit_id += 1
        hit_index = int(hit_index)

        i0 = max(0, hit_index - pre_n)
        i1 = min(n_samples, hit_index + post_n)
        if i0 < 0 or i1 > stereo.hammer.size:
            continue

        t_hit = hit_index / fs
        t_start = i0 / fs
        t_end = i1 / fs

        windows.append(
            HitWindow(
                hit_id=hit_id,
                hit_index=hit_index,
                t_hit=t_hit,
                t_start=t_start,
                t_end=t_end,
                hammer=stereo.hammer[i0:i1].copy(),
                accel=stereo.accel[i0:i1].copy(),
            )
        )
    return windows

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

    hit_index, thr = detect_hits(
        stereo.hammer,
        stereo.fs,
        baseline_s=baseline_s,
        threshold_sigma=threshold_sigma,
        min_separation_s=min_separation_s,
        polarity=polarity,
    )

    windows = extract_hit_windows(stereo, hit_index, pre_s=pre_s, post_s=post_s)

    report = HitDetectionReport(
        n_hits_found=int(len(hit_index)),
        n_hits_used=int(len(windows)),
        threshold=float(thr),
        min_separation_s=float(min_separation_s),
        pre_s=float(pre_s),
        post_s=float(post_s),
    )
    return stereo, windows, report
