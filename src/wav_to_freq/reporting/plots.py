# ==== FILE: src/wav_to_freq/reporting/plots.py ====

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

from wav_to_freq.impact_io import HitWindow, StereoWav
from wav_to_freq.modal import HitModalResult


# -------------------------
# Utilities
# -------------------------

def _window_to_indices(w: HitWindow, fs: float, *, n_total: int | None = None) -> tuple[int, int]:
    """
    Convert a HitWindow (t_start, t_end) to integer sample indices [i0, i1).
    HitWindow stays timestamp-based; indices are derived only when needed.
    """
    i0 = int(round(w.t_start * fs))
    i1 = int(round(w.t_end * fs))

    if n_total is not None:
        i0 = max(0, min(i0, n_total))
        i1 = max(0, min(i1, n_total))

    if i1 < i0:
        i0, i1 = i1, i0

    return i0, i1


def _hilbert_envelope(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    analytic = signal.hilbert(x)
    return np.abs(analytic)


def _exp_fit_with_offset(t: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """
    Fit y ~= A * exp(-b*(t - t0)) over provided arrays.

    Returns (A, b, r2) in log-space:
        ln(y) = ln(A) - b*(t - t0)

    - Uses t0 = t[0] so the curve “surfs” the envelope start for the fit region.
    - y is clipped to avoid log(0).
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)

    if t.size < 4:
        return (float("nan"), float("nan"), float("nan"))

    t0 = float(t[0])
    dt = t - t0

    eps = np.finfo(float).eps
    yy = np.clip(y, eps, None)
    ln = np.log(yy)

    # linear regression ln = c + m*dt  =>  A=exp(c), b=-m
    m, c = np.polyfit(dt, ln, 1)
    ln_hat = c + m * dt

    ss_res = float(np.sum((ln - ln_hat) ** 2))
    ss_tot = float(np.sum((ln - float(np.mean(ln))) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

    A = float(np.exp(c))
    b = float(-m)
    return A, b, r2


# -------------------------
# Preprocess overview figure
# -------------------------

def plot_overview_two_channels(
    stereo: StereoWav,
    windows: list[HitWindow] | None = None,
    out_png: str | Path | None = None,
    *,
    max_seconds: float | None = 15.0,
) -> Path:
    fs = float(stereo.fs)
    n = stereo.hammer.size
    t = np.arange(n) / fs

    if max_seconds is not None:
        nmax = int(min(n, round(max_seconds * fs)))
        t = t[:nmax]
        hammer = stereo.hammer[:nmax]
        accel = stereo.accel[:nmax]
    else:
        hammer = stereo.hammer
        accel = stereo.accel

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(14, 6), sharex=True)

    ax0.plot(t, hammer, linewidth=0.8)
    ax0.set_ylabel("Hammer (raw)")
    ax0.grid(True, alpha=0.2)

    ax1.plot(t, accel, linewidth=0.8)
    ax1.set_ylabel("Accel (raw)")
    ax1.set_xlabel("Time (s)")
    ax1.grid(True, alpha=0.2)

    if windows:
        for w in windows:
            ax0.axvspan(w.t_start, w.t_end, alpha=0.08)
            ax1.axvspan(w.t_start, w.t_end, alpha=0.08)

    fig.tight_layout()

    if out_png is None:
        out_png = Path("overview_two_channels.png")
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=160)
    plt.close(fig)
    return out_png


# -------------------------
# Per-hit modal figure
# -------------------------

@dataclass(frozen=True)
class EstablishedZones:
    transient_s: float
    established_min_s: float
    established_r2_min: float


def plot_hit_response_report(
    *,
    fs: float,
    window: HitWindow,
    result: HitModalResult,
    out_png: str | Path,
    transient_s: float = 0.20,
) -> Path:
    """
    Per-hit diagnostic plot. Critical rule:
      - If modal analysis provided fit_t0_s/fit_t1_s, we use those for shading + fitted curve.
      - Otherwise we fall back to transient_s heuristics (visual-only).
    """
    fs = float(fs)
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    x_raw = np.asarray(window.accel, dtype=float)
    t = np.arange(x_raw.size, dtype=float) / fs  # time from window start

    # Filter around fn if available
    y = x_raw.copy()
    if np.isfinite(float(result.fn_hz)) and float(result.fn_hz) > 0:
        fn = float(result.fn_hz)
        lo = max(0.5, 0.6 * fn)
        hi = min(0.49 * fs, 1.4 * fn)
        if hi > lo:
            b, a = signal.butter(4, [lo / (0.5 * fs), hi / (0.5 * fs)], btype="bandpass")
            y = signal.filtfilt(b, a, y)

    y = y - float(np.mean(y))
    env = _hilbert_envelope(y)

    # Determine fit region (prefer analysis-owned)
    if result.fit_t0_s is not None and result.fit_t1_s is not None:
        t_est0 = float(result.fit_t0_s) - float(window.t_start)
        t_est1 = float(result.fit_t1_s) - float(window.t_start)
        # clamp
        t_est0 = max(0.0, min(t_est0, float(t[-1]) if t.size else 0.0))
        t_est1 = max(t_est0, min(t_est1, float(t[-1]) if t.size else t_est0))
        t_trans_end = t_est0  # transient ends where established fit begins
    else:
        # fallback visualization only
        t_trans_end = float(transient_s)
        t_est0 = float(transient_s)
        t_est1 = float(t[-1]) if t.size else float(transient_s)

    # Fit curve for display: use the region we chose above
    m_fit = float(result.env_log_m) if np.isfinite(float(result.env_log_m)) else float("nan")
    c_fit = float(result.env_log_c) if np.isfinite(float(result.env_log_c)) else float("nan")

    in_fit = (t >= t_est0) & (t <= t_est1)
    t_fit = t[in_fit]
    env_fit = env[in_fit]

    # If analysis produced c/m (log env slope), use those; otherwise fit locally for plotting
    if t_fit.size >= 4 and np.isfinite(m_fit) and np.isfinite(c_fit):
        # "surf" offset: t0 = t_fit[0] => ln(env)=c + m*(t-t0)
        dt = t_fit - float(t_fit[0])
        fit_curve = np.exp(c_fit + m_fit * dt)
        # r2 for label should match analysis metric
        r2_fit = float(result.env_fit_r2)
        A_fit = float(np.exp(c_fit))
        b_fit = float(-m_fit)
    else:
        A_fit, b_fit, r2_fit = _exp_fit_with_offset(t_fit, env_fit)
        fit_curve = A_fit * np.exp(-b_fit * (t_fit - float(t_fit[0]))) if t_fit.size else np.array([])

    # Plot
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(14, 6), sharex=True)

    ax0.plot(t, x_raw, linewidth=0.8, label="raw")
    ax0.grid(True, alpha=0.2)
    ax0.set_ylabel("Accel (raw)")
    ax0.legend(loc="upper right")

    ax1.plot(t, y, linewidth=0.8, label="filtered")
    ax1.plot(t, env, linewidth=1.2, label="envelope")

    # shaded zones
    ax1.axvspan(0.0, t_trans_end, alpha=0.25, label="Transient")
    ax1.axvspan(t_est0, t_est1, alpha=0.10, label="Established")

    # fitted curve on established region only
    if t_fit.size and fit_curve.size:
        ax1.plot(t_fit, fit_curve, linewidth=2.5, label=f"fit (R²={r2_fit:.3f})")

    ax1.set_xlabel("Time from window start (s)")
    ax1.set_ylabel("Accel (filtered / envelope)")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)

    return out_png

