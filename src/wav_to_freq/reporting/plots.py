from pathlib import Path
from typing import Sequence

import numpy as np
import matplotlib.pyplot as plt

from wav_to_freq.impact_io import HitWindow, StereoWav

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
