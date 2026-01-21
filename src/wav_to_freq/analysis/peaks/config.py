from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PsdConfig:
    """Welch PSD configuration.

    This matches E25: make the PSD configuration explicit, deterministic, and loggable.
    """

    df_target_hz: float = 0.25
    nperseg_min: int = 256
    nperseg_max: int = 4096
    overlap_frac: float = 0.50
    window: str = "hann"
    detrend: str = "constant"
    scaling: str = "density"
    snap_pow2: bool = True


@dataclass(frozen=True)
class PeakConfig:
    """PSD peak selection configuration (E26-E29)."""

    noise_floor_percentile: float = 60.0
    min_peak_snr_db: float = 6.0
    max_candidate_peaks: int = 5

    # Peak de-duplication (E28): merge near-duplicate peaks.
    merge_min_spacing_hz: float = 0.5
    merge_min_spacing_frac: float = 0.03

    # Coupled / near-degenerate region flagging (E29): keep both, add flags.
    coupled_max_spacing_hz: float = 1.0
    coupled_max_spacing_frac: float = 0.06

    # Per-hit refinement search window around each global peak.
    refine_search_hz: float = 1.0


def choose_nperseg(fs: float, cfg: PsdConfig, *, n_samples: int) -> int:
    """Choose Welch nperseg from df_target_hz and data length."""

    if cfg.df_target_hz <= 0:
        raise ValueError(f"df_target_hz must be > 0. Got {cfg.df_target_hz}")

    n_target = int(round(float(fs) / float(cfg.df_target_hz)))

    n = max(cfg.nperseg_min, min(cfg.nperseg_max, n_target))
    n = min(n, int(n_samples))

    if cfg.snap_pow2:
        # Snap down to nearest power of two (deterministic; faster FFT).
        p = 1
        while p * 2 <= n:
            p *= 2
        n = p

    return max(16, int(n))
