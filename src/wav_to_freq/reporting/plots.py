# ==== FILE: src/wav_to_freq/reporting/plots.py ====

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

from wav_to_freq.impact_io import HitWindow, StereoWav
from wav_to_freq.modal import HitModalResult


def _hilbert_envelope(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    analytic = signal.hilbert(x)
    return np.abs(analytic)


def _exp_fit_with_offset(t: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)

    if t.size < 4:
        return (float("nan"), float("nan"), float("nan"))

    t0 = float(t[0])
    dt = t - t0

    eps = np.finfo(float).eps
    yy = np.clip(y, eps, None)
    ln = np.log(yy)

    m, c = np.polyfit(dt, ln, 1)
    ln_hat = c + m * dt

    ss_res = float(np.sum((ln - ln_hat) ** 2))
    ss_tot = float(np.sum((ln - float(np.mean(ln))) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

    A = float(np.exp(c))
    b = float(-m)
    return A, b, r2


def _analysis_segment_in_window(
    window: HitWindow, result: HitModalResult, fs: float
) -> tuple[int, int]:
    fs = float(fs)

    t0_rel = float(result.t0_s) - float(window.t_start)
    t1_rel = float(result.t1_s) - float(window.t_start)

    i0 = int(round(t0_rel * fs))
    i1 = int(round(t1_rel * fs))

    n = int(np.asarray(window.accel).size)
    i0 = max(0, min(i0, n))
    i1 = max(0, min(i1, n))
    if i1 < i0:
        i0, i1 = i1, i0

    if i1 - i0 < 8:
        i0 = 0
        i1 = n

    return i0, i1


def _pick_psd_peaks(
    f: np.ndarray,
    db: np.ndarray,
    *,
    n_modes: int,
    fmin_hz: float,
    fmax_hz: float,
) -> list[int]:
    f = np.asarray(f, dtype=float)
    db = np.asarray(db, dtype=float)

    band = (f >= float(fmin_hz)) & (f <= float(fmax_hz))
    if not np.any(band):
        return []

    fb = f[band]
    dbb = db[band]
    if fb.size < 8:
        return []

    dist = max(1, int(round(0.01 * dbb.size)))
    peaks, props = signal.find_peaks(dbb, distance=dist, prominence=3.0)

    if peaks.size == 0:
        k = int(np.argmax(dbb))
        return [np.flatnonzero(band)[0] + k]

    heights = dbb[peaks]
    order = np.argsort(heights)[::-1]
    peaks = peaks[order][: max(1, int(n_modes))]

    band_idx = np.flatnonzero(band)
    return [int(band_idx[p]) for p in peaks]


def _auto_psd_band(
    *,
    fs: float,
    fn_hz: float | None,
    fmin_default: float,
    fmax_default: float | None,
) -> tuple[float, float]:
    """
    Decide PSD display band.

    If fmax_default is provided -> use it.
    If fmax_default is None -> auto:
      - If fn is finite: show [max(0.5, fn/10), min(0.49*fs, 1.5*fn)] (with some padding)
      - Else: structural default [fmin_default, 50 Hz] (or 200 if you prefer)
    """
    fs = float(fs)
    nyq = 0.49 * fs

    fmin = float(fmin_default)

    if fmax_default is not None:
        fmax = float(fmax_default)
        return max(0.0, fmin), max(fmin + 1e-9, min(fmax, nyq))

    # auto mode
    fn = float(fn_hz) if fn_hz is not None else float("nan")
    if np.isfinite(fn) and fn > 0:
        fmin_auto = max(fmin, fn / 10.0)
        fmax_auto = min(nyq, fn * 1.5)
        # ensure some minimum span
        fmax_auto = max(fmax_auto, fmin_auto + 20.0)
        return fmin_auto, fmax_auto

    # no fn -> conservative structural view
    return max(0.0, fmin), min(nyq, 50.0)


# -------------------------
# Preprocess overview figure (unchanged)
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
    # spectrum / mode labeling
    n_modes: int = 5,
    psd_fmin_hz: float = 0.5,
    psd_fmax_hz: float | None = None,  # <-- None means auto-scale
) -> Path:
    fs = float(fs)
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    x_raw = np.asarray(window.accel, dtype=float)
    t = np.arange(x_raw.size, dtype=float) / fs

    # ---------- Filter around fn (time-domain row #2) ----------
    y = x_raw.copy()
    if np.isfinite(float(result.fn_hz)) and float(result.fn_hz) > 0:
        fn = float(result.fn_hz)
        lo = max(0.5, 0.6 * fn)
        hi = min(0.49 * fs, 1.4 * fn)
        if hi > lo:
            b, a = signal.butter(
                4, [lo / (0.5 * fs), hi / (0.5 * fs)], btype="bandpass"
            )
            y = signal.filtfilt(b, a, y)

    y = y - float(np.mean(y))
    env = _hilbert_envelope(y)

    # ---------- Fit region shading ----------
    if result.fit_t0_s is not None and result.fit_t1_s is not None:
        t_est0 = float(result.fit_t0_s) - float(window.t_start)
        t_est1 = float(result.fit_t1_s) - float(window.t_start)
        t_est0 = max(0.0, min(t_est0, float(t[-1]) if t.size else 0.0))
        t_est1 = max(t_est0, min(t_est1, float(t[-1]) if t.size else t_est0))
        t_trans_end = t_est0
    else:
        t_trans_end = float(transient_s)
        t_est0 = float(transient_s)
        t_est1 = float(t[-1]) if t.size else float(transient_s)

    # Fit curve for display
    m_fit = (
        float(result.env_log_m)
        if np.isfinite(float(result.env_log_m))
        else float("nan")
    )
    c_fit = (
        float(result.env_log_c)
        if np.isfinite(float(result.env_log_c))
        else float("nan")
    )

    in_fit = (t >= t_est0) & (t <= t_est1)
    t_fit = t[in_fit]
    env_fit = env[in_fit]

    if t_fit.size >= 4 and np.isfinite(m_fit) and np.isfinite(c_fit):
        dt = t_fit - float(t_fit[0])
        fit_curve = np.exp(c_fit + m_fit * dt)
        r2_fit = float(result.env_fit_r2)
    else:
        A_fit, b_fit, r2_fit = _exp_fit_with_offset(t_fit, env_fit)
        fit_curve = (
            A_fit * np.exp(-b_fit * (t_fit - float(t_fit[0])))
            if t_fit.size
            else np.array([])
        )

    # ---------- PSD band auto-scale ----------
    psd_lo, psd_hi = _auto_psd_band(
        fs=fs,
        fn_hz=float(result.fn_hz) if np.isfinite(float(result.fn_hz)) else None,
        fmin_default=psd_fmin_hz,
        fmax_default=psd_fmax_hz,
    )

    # ---------- PSD (analysis-consistent segment) ----------
    i0_psd, i1_psd = _analysis_segment_in_window(window, result, fs)
    seg = np.asarray(x_raw[i0_psd:i1_psd], dtype=float).copy()
    seg = seg - float(np.mean(seg))

    if seg.size >= 16:
        nperseg = min(4096, max(256, seg.size // 2))
        f, pxx = signal.welch(seg, fs=fs, nperseg=nperseg)
        db = 10.0 * np.log10(pxx + np.finfo(float).eps)
        peak_idx = _pick_psd_peaks(
            f, db, n_modes=n_modes, fmin_hz=psd_lo, fmax_hz=psd_hi
        )
    else:
        f = np.array([], dtype=float)
        db = np.array([], dtype=float)
        peak_idx = []

    # ---------- Plot (3 rows) ----------
    fig, (ax0, ax1, ax2) = plt.subplots(3, 1, figsize=(14, 8.5), sharex=False)

    ax0.plot(t, x_raw, linewidth=0.8, label="raw")
    ax0.grid(True, alpha=0.2)
    ax0.set_ylabel("Accel (raw)")
    ax0.legend(loc="upper right")

    ax1.plot(t, y, linewidth=0.8, label="filtered")
    ax1.plot(t, env, linewidth=1.2, label="envelope")
    ax1.axvspan(0.0, t_trans_end, alpha=0.25, label="Transient", zorder=0)
    ax1.axvspan(t_est0, t_est1, alpha=0.10, label="Established", zorder=0)
    if t_fit.size and fit_curve.size:
        ax1.plot(
            t_fit,
            fit_curve,
            linewidth=2.5,
            linestyle="--",
            label=f"fit (R²={r2_fit:.3f})",
        )
    ax1.set_xlabel("Time from window start (s)")
    ax1.set_ylabel("Accel (filtered / envelope)")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper right")

    if f.size and db.size:
        ax2.plot(f, db, linewidth=1.0, label="PSD (Welch)")

        if np.isfinite(float(result.fn_hz)):
            fn = float(result.fn_hz)
            ax2.axvline(
                fn, linewidth=1.2, linestyle="--", alpha=0.9, label=f"fn={fn:.2f} Hz"
            )

        for j, k in enumerate(peak_idx, start=1):
            fj = float(f[k])
            dj = float(db[k])
            ax2.plot([fj], [dj], marker="o", markersize=4)
            ax2.annotate(
                f"f{j}={fj:.2f}",
                xy=(fj, dj),
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=9,
            )

        ax2.set_xlim(psd_lo, psd_hi)
        ax2.set_ylabel("PSD (dB)")
        ax2.set_xlabel("Frequency (Hz)")
        ax2.grid(True, alpha=0.2)
        ax2.legend(loc="upper right")
    else:
        ax2.text(
            0.5,
            0.5,
            "PSD unavailable (segment too short)",
            transform=ax2.transAxes,
            ha="center",
            va="center",
        )
        ax2.set_axis_off()

    title_bits = [f"H{result.hit_id:03d}"]
    if np.isfinite(float(result.fn_hz)):
        title_bits.append(f"fn={float(result.fn_hz):.2f} Hz")
    if np.isfinite(float(result.zeta)):
        title_bits.append(f"ζ={float(result.zeta):.4f}")
    if np.isfinite(float(result.env_fit_r2)):
        title_bits.append(f"R²={float(result.env_fit_r2):.3f}")
    if result.reject_reason:
        title_bits.append(f"REJECT: {result.reject_reason}")

    fig.suptitle("  |  ".join(title_bits), y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_png, dpi=160)
    plt.close(fig)

    return out_png
