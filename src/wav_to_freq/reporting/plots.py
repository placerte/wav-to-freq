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

