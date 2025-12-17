from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

import numpy as np
import soundfile as sf
from scipy import signal


# Keep it boring for LSPs: values are "left" or "right"
ChannelStr = str

EPS = 1e-30


# -------------------------
# Data containers
# -------------------------

@dataclass
class AutoDetectInfo:
    method: str
    score_left: float
    score_right: float
    picked: ChannelStr

    @property
    def confidence_hi_lo(self) -> float:
        lo = min(self.score_left, self.score_right)
        hi = max(self.score_left, self.score_right)
        return hi / (lo +EPS)

@dataclass(frozen=True)
class StereoWav:
    """Raw stereo acquisition: hammer + response in the same WAV."""
    fs: float
    hammer: np.ndarray
    accel: np.ndarray
    hammer_channel: ChannelStr  # "left" or "right"
    path: Path
    autodetect: AutoDetectInfo | None = None


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

def _as_f64(x: np.ndarray) -> np.ndarray:
    return np.asarray(x, dtype=np.float64)


def _validate_channel(ch: ChannelStr) -> None:
    if ch not in ("left", "right"):
        raise ValueError(f"hammer_channel must be 'left' or 'right'. Got {ch!r}")


def _robust_sigma_mad(x: np.ndarray) -> float:
    """Robust sigma estimate based on MAD."""
    x = _as_f64(x)
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med)) + EPS)
    return 1.4826 * mad


def _moving_mean(x: np.ndarray, win: int) -> np.ndarray:
    """Fast moving average using convolution. win must be >= 1."""
    x = _as_f64(x)
    if win <= 1:
        return x
    k = np.ones(int(win), dtype=np.float64) / float(win)
    return np.convolve(x, k, mode="same")


def _highpass(x: np.ndarray, fs: float, fc_hz: float = 200.0, order: int = 4) -> np.ndarray:
    """
    High-pass filter to emphasize the hammer impulse vs the long ringdown.
    fc_hz=200 Hz is a decent default for typical impact testing recordings.
    """
    x = _as_f64(x)
    nyq = 0.5 * fs
    fc = max(1.0, min(fc_hz, 0.45 * nyq))
    sos = signal.butter(order, fc / nyq, btype="highpass", output="sos")
    return signal.sosfiltfilt(sos, x)


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

    left = _as_f64(data[:, 0])
    right = _as_f64(data[:, 1])
    return left, right, float(fs), p


# -------------------------
# Stage 1: auto-pick hammer channel
# -------------------------

def _channel_impulsiveness_score(
    x: np.ndarray,
    fs: float,
    *,
    min_separation_s: float,
) -> float:
    """
    Score a channel for being the hammer channel.

    Key idea for your recordings:
      - hammer: short, concentrated energy near the hit instant (even if lower amplitude)
      - response: larger amplitude but energy spread in time (ringdown)

    We:
      1) high-pass
      2) take abs envelope
      3) find a few very large peaks (quantile threshold)
      4) compute early/late energy ratio around each peak
    """
    xhp = _highpass(x, fs, fc_hz=200.0)
    env = np.abs(xhp)

    # mild smoothing so the peak finder doesn't latch onto every oscillation
    smooth = _moving_mean(env, int(max(1, round(0.002 * fs))))  # ~2 ms

    # pick only the very top events
    q = float(np.quantile(smooth, 0.995))
    floor = float(np.quantile(smooth, 0.98))
    thr = max(q, floor)

    min_sep = int(max(1, round(min_separation_s * fs)))
    peaks, props = signal.find_peaks(smooth, height=thr, distance=min_sep)

    if peaks.size == 0:
        # fallback: "crest-like" metric on high-passed signal
        rms = float(np.sqrt(np.mean(xhp * xhp)) + EPS)
        num = float(np.quantile(np.abs(xhp), 0.999) + EPS)
        return num / rms

    # energy windows (tuned for impact tests)
    early = int(max(1, round(0.006 * fs)))          # 6 ms
    late0 = int(max(1, round(0.050 * fs)))          # start 50 ms after peak
    late1 = int(max(late0 + 1, round(0.150 * fs)))  # end 150 ms after peak

    ratios: list[float] = []
    n = smooth.size
    for i in peaks[: min(peaks.size, 30)]:
        i = int(i)
        e0 = smooth[i : min(n, i + early)]
        l0 = smooth[min(n, i + late0) : min(n, i + late1)]
        e = float(np.sum(e0) + EPS)
        l = float(np.sum(l0) + EPS)
        ratios.append(e / l)

    # hammer should have a higher median early/late ratio
    return float(np.median(ratios)) if ratios else 0.0


def _kurtosis_spikiness(x: np.ndarray) -> float:
    """
    Kurtosis (non-fisher): E[(x-mu)^4] / (E[(x-mu)^2]^2)
    Bigger => more "spiky"/impulsive.
    """
    x = np.asarray(x, dtype=np.float64)
    x = x - float(np.mean(x))
    m2 = float(np.mean(x * x)) + 1e-30
    m4 = float(np.mean((x * x) * (x * x))) + 1e-30
    return m4 / (m2 * m2)


def _auto_pick_hammer_channel(left: np.ndarray, right: np.ndarray, fs: float) -> tuple[str, float, float]:
    # high-pass helps remove low-frequency drift and emphasizes impulse character
    L = _highpass(left, fs, fc_hz=200.0)
    R = _highpass(right, fs, fc_hz=200.0)

    sL = _kurtosis_spikiness(L)
    sR = _kurtosis_spikiness(R)

    ch = "left" if sL >= sR else "right"
    return ch, float(sL), float(sR)

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
    hammer = _as_f64(hammer)

    xhp = _highpass(hammer, fs, fc_hz=highpass_hz)
    if polarity == "abs":
        y = np.abs(xhp)
    elif polarity == "positive":
        y = xhp
    else:
        y = -xhp

    y = _moving_mean(y, int(max(1, round(smooth_s * fs))))

    # baseline noise estimate
    n0 = int(max(1000, min(y.size, round(baseline_s * fs))))
    base = y[:n0]

    sigma = _robust_sigma_mad(base)
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
    hammer_channel: ChannelStr | None = None,
    min_separation_s: float = 0.30,
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

    if hammer_channel is None:
        picked, score_left, score_right = _auto_pick_hammer_channel(left, right, fs)
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
    hammer_channel: ChannelStr | None = None,
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
    stereo = load_stereo_wav(wav_path, hammer_channel=hammer_channel, min_separation_s=min_separation_s)

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

