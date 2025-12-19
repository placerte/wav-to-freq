# ==== FILE: src/wav_to_freq/reporting/plots.py ====

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
from scipy.signal import welch

from wav_to_freq.impact_io import HitWindow, StereoWav
from wav_to_freq.modal import HitModalResult


def plot_hit_response_with_damping(
    *,
    fs: float,
    t_abs: NDArray[np.float64],
    x: NDArray[np.float64],
    result: HitModalResult,
    out_png: Path,
) -> None:
    """
    Time plot with:
      - raw accel
      - envelope (Hilbert abs, approximate via abs(hilbert()) in modal; here we just show |x| smoothed-ish)
      - fitted exponential envelope based on env_log_c/env_log_m
      - shaded early transient vs established decay using result.fit_t0_s/result.fit_t1_s
    """
    out_png.parent.mkdir(parents=True, exist_ok=True)

    t_abs = np.asarray(t_abs, dtype=float)
    x = np.asarray(x, dtype=float)

    # Relative time from start of ringdown segment
    t0 = float(t_abs[0])
    t_rel = t_abs - t0

    fig = plt.figure(figsize=(11, 4.2))
    ax = fig.add_subplot(1, 1, 1)

    ax.plot(t_rel, x, lw=0.9, label="accel")

    # If we have fit bounds, shade regions
    if np.isfinite(result.fit_t0_s):
        fit_start_rel = float(result.fit_t0_s - t0)
        fit_end_rel = float(result.fit_t1_s - t0) if np.isfinite(result.fit_t1_s) else float(t_rel[-1])

        fit_start_rel = max(float(t_rel[0]), min(fit_start_rel, float(t_rel[-1])))
        fit_end_rel = max(fit_start_rel, min(fit_end_rel, float(t_rel[-1])))

        # Early transient
        ax.axvspan(float(t_rel[0]), fit_start_rel, alpha=0.08, label="early transient")
        # Established decay (fit zone)
        ax.axvspan(fit_start_rel, fit_end_rel, alpha=0.10, label="established decay")
        ax.axvline(fit_start_rel, lw=1.2, linestyle="--", label="fit start")

    # Plot fitted exponential envelope, if available
    if np.isfinite(result.env_log_c) and np.isfinite(result.env_log_m):
        # The fit is log(env) = c + m t_rel  => env = exp(c + m t_rel)
        env_fit = np.exp(result.env_log_c + result.env_log_m * t_rel)

        # To make it comparable to accel amplitude, plot ± envelope
        ax.plot(t_rel, +env_fit, lw=1.2, label="fit envelope (+)")
        ax.plot(t_rel, -env_fit, lw=1.2, label="fit envelope (-)")

    title = f"H{result.hit_id:03d}  fn={result.fn_hz:.2f} Hz  zeta={result.zeta:.5f}  R²={result.env_fit_r2:.3f}"
    if result.reject_reason:
        title += f"  REJECT: {result.reject_reason}"
    ax.set_title(title)

    ax.set_xlabel("t (s) relative to ringdown start")
    ax.set_ylabel("accel (a.u.)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def plot_hit_spectrum(
    *,
    x: NDArray[np.float64],
    fs: float,
    result: HitModalResult,
    out_png: Path,
    fmin_hz: float = 0.0,
    fmax_hz: float = 200.0,
) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)

    x = np.asarray(x, dtype=float)
    nperseg = int(min(len(x), max(256, 2 ** int(np.floor(np.log2(len(x)))))))
    f, pxx = welch(x, fs=fs, nperseg=nperseg)

    mask = (f >= fmin_hz) & (f <= fmax_hz)
    f2 = f[mask]
    p2 = pxx[mask]

    fig = plt.figure(figsize=(11, 3.8))
    ax = fig.add_subplot(1, 1, 1)

    ax.plot(f2, p2, lw=1.0, label="PSD")

    if np.isfinite(result.fn_hz):
        ax.axvline(result.fn_hz, linestyle="--", lw=1.2, label=f"fn={result.fn_hz:.2f} Hz")

    ax.set_title(f"H{result.hit_id:03d} spectrum")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("PSD (a.u.)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)

def plot_overview_two_channels(
    stereo: StereoWav,
    windows: Sequence[HitWindow],
    out_path: Path,
    *,
    max_seconds: float | None = None,
    show_hit_markers: bool = True,
) -> Path:
    """
    Overview plot (full recording):
      - Top: hammer channel
      - Bottom: response/accel channel
    Both share the same time axis (aligned), with independent y scales.
    """
    fs = float(stereo.fs)

    hammer = np.asarray(stereo.hammer)
    accel = np.asarray(stereo.accel)
    hit_labels = [f"H{i+1:03d}" for i in range(len(windows))]

    n = min(hammer.size, accel.size)

    if max_seconds is None:
        n_plot = n
    else:
        n_plot = int(min(n, max_seconds * fs))

    t = np.arange(n_plot) / fs

    fig, (ax_h, ax_a) = plt.subplots(
        2, 1,
        sharex=True,
        figsize=(10, 6),
    )

    _add_hit_annotations(ax_h, stereo.fs, windows, hit_labels, label_every=1)
    _add_hit_annotations(ax_a, stereo.fs, windows, hit_labels, label_every=0)  # no labels on bottom

    ax_h.plot(t, hammer[:n_plot])
    ax_h.set_title("Overview (aligned): hammer + response")
    ax_h.set_ylabel("Hammer")

    ax_a.plot(t, accel[:n_plot])
    ax_a.set_ylabel("Response")
    ax_a.set_xlabel("Time (s)")

    if show_hit_markers:
        for w in windows:
            if w.hit_index < n_plot:
                x = w.hit_index / fs
                ax_h.axvline(x)
                ax_a.axvline(x)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path

def _add_hit_annotations(ax, fs, windows, labels, y_text=None, label_every=1):
    # y_text: where to put labels in axis coords (None => auto)
    if y_text is None:
        y_text = 0.92  # near top of axis (axes fraction)

    for i, (w, lab) in enumerate(zip(windows, labels)):
        t0 = float(w.t_start)
        t1 = float(w.t_end)
        th = float(w.t_hit)

        # alternating shading
        ax.axvspan(t0, t1, alpha=0.12, zorder=0)

        # hit marker
        ax.axvline(th, lw=1, alpha=0.35)

        # optional label (only every N hits)
        if label_every and (i % label_every == 0):
            ax.text(
                th, y_text, lab,
                transform=ax.get_xaxis_transform(),  # x in data, y in axes fraction
                ha="center", va="top",
                fontsize=8, alpha=0.85,
            )
