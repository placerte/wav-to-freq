from pathlib import Path
from typing import Sequence

import numpy as np
import matplotlib.pyplot as plt
from numpy.typing import NDArray

from wav_to_freq.impact_io import HitWindow, StereoWav
from wav_to_freq.modal import HitModalResult

from scipy.signal import hilbert, welch, butter, filtfilt

def plot_hammer_with_hit_markers(
    stereo: StereoWav,
    windows: Sequence[HitWindow],
    out_path: Path,
    *,
    max_seconds: float | None = None,
) -> Path:
    """
    Plot full hammer signal with vertical lines at detected hit times.
    """
    fs = float(stereo.fs)
    hammer = np.asarray(stereo.hammer)
    n = hammer.size

    if max_seconds is None:
        n_plot = n
    else:
        n_plot = int(min(n, max_seconds * fs))

    t = np.arange(n_plot) / fs
    y = hammer[:n_plot]

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(t, y)

    for w in windows:
        if w.hit_index < n_plot:
            ax.axvline(w.hit_index / fs)

    ax.set_title("Hammer signal with detected hits")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path

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

    w: HitWindow

    for i, (w, lab) in enumerate(zip(windows, labels)):
        # assuming w.start_idx, w.end_idx, w.hit_idx exist
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


def _bandpass(x: NDArray[np.float64], fs: float, *, low_hz: float, high_hz: float) -> NDArray[np.float64]:
    """Simple Butterworth bandpass used for plotting (mode isolation)."""
    nyq = 0.5 * float(fs)
    low = max(1e-6, float(low_hz) / nyq)
    high = min(0.999999, float(high_hz) / nyq)
    if high <= low:
        return x
    b, a = butter(N=4, Wn=[low, high], btype="bandpass")
    return filtfilt(b, a, x)

def plot_hit_response_with_damping(
    *,
    t_abs: NDArray[np.float64],
    x: NDArray[np.float64],
    fs: float,
    result: HitModalResult,
    out_png: Path,
) -> None:
    """
    Plot isolated ringdown window in time domain.

    Shows:
      - raw detrended accel (thin)
      - mode-isolated (bandpassed) accel (optional, thicker)
      - envelope of the mode-isolated signal
      - exponential fit derived from the same envelope regression (if available)
    """
    # relative time for nicer axis
    t0 = float(t_abs[0])
    t = t_abs - t0

    x_raw = np.asarray(x, dtype=np.float64)
    x_raw = x_raw - float(np.mean(x_raw))

    # Defaults for plotting clarity (raw can be very dense at high fn)
    lw_raw = 0.35
    lw_bp = 0.8
    lw_env = 1.0
    lw_fit = 2.0
    alpha_raw = 0.8
    alpha_bp = 0.9
    alpha_env = 0.95

    # If we know fn, isolate mode-0 for envelope/fit comparison
    have_mode = bool(np.isfinite(result.fn_hz) and result.fn_hz > 0)
    if have_mode:
        fn = float(result.fn_hz)
        x_bp = _bandpass(x_raw, float(fs), low_hz=max(0.05, 0.7 * fn), high_hz=1.3 * fn)
        env = np.abs(hilbert(x_bp)) + 1e-12
    else:
        x_bp = x_raw
        env = np.abs(hilbert(x_raw)) + 1e-12

    plt.figure()
    plt.plot(t, x_raw, label="accel (raw, detrended)", lw=lw_raw, alpha=alpha_raw)

    # Only plot bandpassed trace if it's meaningfully different (i.e., we had fn)
    if have_mode:
        plt.plot(t, x_bp, label="accel (mode-isolated)", lw=lw_bp, alpha=alpha_bp)

    plt.plot(t, env, label="envelope (mode-isolated)", lw=lw_env, alpha=alpha_env)

    txt = f"fn={result.fn_hz:.2f} Hz, zeta={result.zeta:.5f}, R²={result.env_fit_r2:.3f}"

    # Plot exponential fit computed from the same log-envelope regression, if present
    have_fit = bool(np.isfinite(result.env_log_c) and np.isfinite(result.env_log_m))
    if have_fit:
        c = float(result.env_log_c)
        m = float(result.env_log_m)
        fit = np.exp(c + m * t)
    if have_fit:
        c = float(result.env_log_c)
        m = float(result.env_log_m)
        fit = np.exp(c + m * t)
        plt.plot(t, fit, label="exp fit (log-env regression)", lw=lw_fit)
    else:
        # Fallback: use zeta,fn anchoring (may not align perfectly with envelope scale)
        if np.isfinite(result.zeta) and result.zeta > 0 and have_mode:
            omega_n = 2.0 * np.pi * float(result.fn_hz)
            alpha = float(result.zeta) * omega_n
            A0 = float(env[max(0, min(5, len(env)-1))])  # avoid t=0 transient a bit
            fit = A0 * np.exp(-alpha * t)
            plt.plot(t, fit, label="exp fit (from zeta, fn)", lw=lw_fit)

    plt.title(f"Hit {result.hit_id} ringdown\n{txt}")
    plt.xlabel("t (s) from ringdown start")
    plt.ylabel("accel (a.u.)")
    plt.legend()
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=160)
    plt.close()
def plot_hit_spectrum(
    *,
    x: NDArray[np.float64],
    fs: float,
    result: HitModalResult,
    out_png: Path,
    fmin_hz: float = 0.0,
    fmax_hz: float | None = None,
) -> None:
    """
    Welch PSD on the isolated ringdown segment.
    """
    x0 = x - float(np.mean(x))

    nperseg = int(min(len(x0), max(1024, 2 ** int(np.floor(np.log2(len(x0)))))))
    f, pxx = welch(x0, fs=fs, nperseg=nperseg)

    if fmax_hz is None:
        fmax_hz = fs / 2.0

    mask = (f >= fmin_hz) & (f <= fmax_hz)

    plt.figure()
    plt.semilogy(f[mask], pxx[mask])
    if np.isfinite(result.fn_hz):
        plt.axvline(float(result.fn_hz), linestyle="--")  # default color
    plt.title(f"Hit {result.hit_id} spectrum (Welch PSD)")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("PSD (a.u.)")
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=160)
    plt.close()
