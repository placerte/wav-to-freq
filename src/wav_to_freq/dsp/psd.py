from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.signal import welch

from wav_to_freq.analysis.peaks.config import PsdConfig, choose_nperseg


def compute_welch_psd(
    x: NDArray[np.float64],
    *,
    fs: float,
    cfg: PsdConfig,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute Welch PSD with deterministic parameter selection."""

    xx = np.asarray(x, dtype=np.float64)
    if xx.size < 16:
        return np.asarray([], dtype=np.float64), np.asarray([], dtype=np.float64)

    nperseg = choose_nperseg(fs, cfg, n_samples=int(xx.size))
    noverlap = int(round(cfg.overlap_frac * nperseg))
    noverlap = max(0, min(noverlap, nperseg - 1))

    f, pxx = welch(
        xx,
        fs=float(fs),
        window=cfg.window,
        nperseg=nperseg,
        noverlap=noverlap,
        detrend=cfg.detrend,
        scaling=cfg.scaling,
    )
    return np.asarray(f, dtype=np.float64), np.asarray(pxx, dtype=np.float64)
