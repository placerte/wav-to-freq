# ==== FILE: src/wav_to_freq/reporting/plots.py ====

from __future__ import annotations

from pathlib import Path
from typing import Sequence, Optional, Any

import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, hilbert

from wav_to_freq.impact_io import HitWindow, StereoWav
from wav_to_freq.modal import HitModalResult


def _as_f64(x: NDArray[np.floating]) -> NDArray[np.float64]:
    return np.asarray(x, dtype=np.float64)


def _bandpass(
    x: NDArray[np.float64],
    fs: float,
    *,
    f0_hz: float,
    rel_bw: float = 0.15,
    order: int = 4,
) -> NDArray[np.float64]:
    x = _as_f64(x)
    fs = float(fs)
    if not np.isfinite(f0_hz) or f0_hz <= 0 or fs <= 0:
        return x

    nyq = 0.5 * fs
    lo = max(1.0, f0_hz * (1.0 - rel_bw))
    hi = min(0.45 * fs, f0_hz * (1.0 + rel_bw))
    if hi <= lo or hi >= nyq:
        return x

    b, a = butter(order, [lo / nyq, hi / nyq], btype="bandpass")
    return filtfilt(b, a, x)


def _envelope(x: NDArray[np.float64]) -> NDArray[np.float64]:
    x = _as_f64(x)
    if x.size == 0:
        return x
    return np.abs(hilbert(x))


def _window_to_indices(w: Any, fs: float, n: int) -> tuple[int, int] | None:
    """
    Convert a HitWindow to (i0, i1) indices for shading.

    Supports:
      - w.i0 and w.i1 as integer attributes
      - w.i0(fs) and w.i1(fs) as methods
      - w.t_start / w.t_end timestamps (fallback)
    """
    fs = float(fs)

    # 1) attribute-style i0/i1
    i0_attr = getattr(w, "i0", None)
    i1_attr = getattr(w, "i1", None)
    if isinstance(i0_attr, (int, np.integer)) and isinstance(i1_attr, (int, np.integer)):
        i0 = int(i0_attr)
        i1 = int(i1_attr)
        return max(0, min(i0, n - 1)), max(0, min(i1, n))

    # 2) method-style i0(fs)/i1(fs)
    if callable(i0_attr) and callable(i1_attr) and fs > 0:
        try:
            i0 = int(i0_attr(fs))
            i1 = int(i1_attr(fs))
            return max(0, min(i0, n - 1)), max(0, min(i1, n))
        except TypeError:
            # signature mismatch
            pass

    # 3) timestamp fallback: round(t * fs)
    t0 = getattr(w, "t_start", None)
    t1 = getattr(w, "t_end", None)
    if isinstance(t0, (int, float)) and isinstance(t1, (int, float)) and fs > 0:
        i0 = int(round(float(t0) * fs))
        i1 = int(round(float(t1) * fs))
        return max(0, min(i0, n - 1)), max(0, min(i1, n))

    return None


def plot_overview_two_channels(
    stereo: StereoWav,
    windows: Sequence[HitWindow],
    out_png: Path,
    *,
    max_seconds: float | None = None,
) -> Path:
    """
    Overview plot: hammer (top) + accel (bottom), with hit windows shaded.
    """
    out_png.parent.mkdir(parents=True, exist_ok=True)

    fs = float(stereo.fs)
    hammer = _as_f64(stereo.hammer)
    accel = _as_f64(stereo.accel)

    n = min(len(hammer), len(accel))
    hammer = hammer[:n]
    accel = accel[:n]

    t = (np.arange(n, dtype=np.float64) / fs) if fs > 0 else np.arange(n, dtype=np.float64)

    if max_seconds is not None and fs > 0:
        nmax = int(max_seconds * fs)
        nmax = max(1, min(nmax, n))
        hammer = hammer[:nmax]
        accel = accel[:nmax]
        t = t[:nmax]
        n = nmax

    fig = plt.figure(figsize=(12, 6))
    ax1 = fig.add_subplot(2, 1, 1)
    ax2 = fig.add_subplot(2, 1, 2, sharex=ax1)

    ax1.plot(t, hammer, lw=0.8)
    ax1.set_title("Hammer channel")
    ax1.set_ylabel("Amplitude")

    ax2.plot(t, accel, lw=0.8)
    ax2.set_title("Accelerometer channel")
    ax2.set_ylabel("Amplitude")
    ax2.set_xlabel("Time (s)")

    # Shade hit windows
    for w in windows:
        idx = _window_to_indices(w, fs=fs, n=n)
        if idx is None:
            continue
        i0, i1 = idx
        if i1 <= i0:
            continue
        ax1.axvspan(float(t[i0]), float(t[i1 - 1]), alpha=0.12)
        ax2.axvspan(float(t[i0]), float(t[i1 - 1]), alpha=0.12)

    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)
    return out_png


def plot_hit_response_report(
    *,
    fs: float,
    window: HitWindow,
    result: HitModalResult,
    out_png: Path,
    transient_s: float = 0.15,
) -> None:
    """
    Per-hit response figure using only HitWindow content + fs.
    """
    out_png.parent.mkdir(parents=True, exist_ok=True)

    fs = float(fs)
    x_raw = _as_f64(window.accel)

    if x_raw.size == 0:
        return

    t_rel = (np.arange(x_raw.size, dtype=np.float64) / fs) if fs > 0 else np.arange(x_raw.size, dtype=np.float64)
    t_abs0 = float(getattr(window, "t_start", 0.0))
    t_abs = t_abs0 + t_rel  # if you ever want absolute time

    # filtered around fn
    x_bp = _bandpass(x_raw, fs, f0_hz=float(result.fn_hz), rel_bw=0.15)
    env = _envelope(x_bp)

    # Established zone boundaries (prefer result.fit_* if present, else transient_s default)
    fit_start_rel = float(max(transient_s, 0.0))
    fit_end_rel = float(t_rel[-1])

    fit_t0_s = getattr(result, "fit_t0_s", float("nan"))
    fit_t1_s = getattr(result, "fit_t1_s", float("nan"))

    # If fit_* are absolute times (seconds), convert to rel (using window.t_start)
    if np.isfinite(fit_t0_s):
        fit_start_rel = max(fit_start_rel, float(fit_t0_s - t_abs0))
    if np.isfinite(fit_t1_s):
        fit_end_rel = min(fit_end_rel, float(fit_t1_s - t_abs0))

    fit_start_rel = max(float(t_rel[0]), min(fit_start_rel, float(t_rel[-1])))
    fit_end_rel = max(fit_start_rel, min(fit_end_rel, float(t_rel[-1])))

    # Build fitted envelope only on established zone; "surf" alignment via time-shift
    c = float(result.env_log_c)
    m = float(result.env_log_m)

    env0 = float(np.interp(fit_start_rel, t_rel, env))
    t_shift = 0.0
    if np.isfinite(c) and np.isfinite(m) and m != 0.0 and env0 > 0.0:
        t_shift = fit_start_rel - (float(np.log(env0)) - c) / m

    mask_fit = (t_rel >= fit_start_rel) & (t_rel <= fit_end_rel)
    t_fit = t_rel[mask_fit]
    y_fit = np.full_like(t_fit, np.nan)
    if t_fit.size > 0 and np.isfinite(c) and np.isfinite(m):
        y_fit = np.exp(c + m * (t_fit - t_shift))

    # Plot: raw + filtered/envelope/fit
    fig = plt.figure(figsize=(12, 6.2))
    ax_raw = fig.add_subplot(2, 1, 1)
    ax_f = fig.add_subplot(2, 1, 2, sharex=ax_raw)

    ax_raw.plot(t_rel, x_raw, lw=0.9)
    ax_raw.set_title(f"H{int(result.hit_id):03d} raw isolated response window")
    ax_raw.set_ylabel("Accel (raw)")

    ax_f.plot(t_rel, x_bp, lw=0.9, label=f"bandpass @ fn={float(result.fn_hz):.3f} Hz")
    ax_f.plot(t_rel, env, lw=1.0, label="envelope |hilbert|")

    # shading
    ax_f.axvspan(float(t_rel[0]), float(fit_start_rel), alpha=0.52, label="Transient")
    ax_f.axvspan(float(fit_start_rel), float(fit_end_rel), alpha=0.10, label="Established")

    # fit only on established zone
    if t_fit.size > 0:
        ax_f.plot(t_fit, y_fit, lw=2.0, label=f"fit (R²={float(result.env_fit_r2):.3f})")

    ax_f.set_title("Filtered response, envelope, and established fit")
    ax_f.set_xlabel("Time from window start (s)")
    ax_f.set_ylabel("Accel (filtered / envelope)")
    ax_f.legend(loc="upper right", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)

