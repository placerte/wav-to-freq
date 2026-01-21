from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from wav_to_freq.analysis.peaks.config import PeakConfig, PsdConfig
from wav_to_freq.analysis.peaks.merge import (
    flag_coupled_regions,
    merge_near_duplicate_peaks,
)
from wav_to_freq.analysis.peaks.psd_peaks import find_candidate_peaks_from_psd
from wav_to_freq.dsp.psd import compute_welch_psd
from wav_to_freq.domain.results import PeakCandidate
from wav_to_freq.domain.types import HitWindow


def _median_psd(pxx_list: list[NDArray[np.float64]]) -> NDArray[np.float64]:
    if not pxx_list:
        return np.asarray([], dtype=np.float64)
    mat = np.stack(pxx_list, axis=0)
    return np.median(mat, axis=0).astype(np.float64)


def compute_global_peaks(
    windows: list[HitWindow],
    *,
    fs: float,
    fmin_hz: float,
    fmax_hz: float,
    psd_cfg: PsdConfig,
    peak_cfg: PeakConfig,
) -> tuple[NDArray[np.float64], NDArray[np.float64], list[PeakCandidate]]:
    """Compute a global candidate peak list across hits (E24)."""

    f_ref: NDArray[np.float64] | None = None
    pxx_list: list[NDArray[np.float64]] = []
    for w in windows:
        f, pxx = compute_welch_psd(
            np.asarray(w.accel, dtype=np.float64), fs=fs, cfg=psd_cfg
        )
        if f.size == 0 or pxx.size == 0:
            continue
        if f_ref is None:
            f_ref = f
        elif f.size != f_ref.size or not np.allclose(f, f_ref):
            # v1: require consistent frequency grids.
            # If this triggers, we should ensure nperseg policy is identical per hit.
            raise ValueError(
                "Per-hit PSD grids are inconsistent; cannot compute global peaks"
            )
        pxx_list.append(pxx)

    if f_ref is None or not pxx_list:
        return np.asarray([], dtype=np.float64), np.asarray([], dtype=np.float64), []

    p_med = _median_psd(pxx_list)

    peaks = find_candidate_peaks_from_psd(
        f_ref,
        p_med,
        fmin_hz=fmin_hz,
        fmax_hz=fmax_hz,
        noise_floor_percentile=peak_cfg.noise_floor_percentile,
        min_peak_snr_db=peak_cfg.min_peak_snr_db,
        max_candidate_peaks=peak_cfg.max_candidate_peaks,
        is_global=True,
    )

    peaks = merge_near_duplicate_peaks(
        peaks,
        abs_hz=peak_cfg.merge_min_spacing_hz,
        frac=peak_cfg.merge_min_spacing_frac,
    )
    peaks = flag_coupled_regions(
        peaks,
        abs_hz=peak_cfg.coupled_max_spacing_hz,
        frac=peak_cfg.coupled_max_spacing_frac,
    )

    # re-rank after merging
    peaks.sort(key=lambda p: float(p.peak_snr_db or -1e300), reverse=True)
    out: list[PeakCandidate] = []
    for rank, p in enumerate(peaks, start=1):
        out.append(
            PeakCandidate(
                peak_rank=rank,
                fi_bin_hz=p.fi_bin_hz,
                fi_refined_hz=p.fi_refined_hz,
                peak_power=p.peak_power,
                noise_floor=p.noise_floor,
                peak_snr_db=p.peak_snr_db,
                is_global=True,
                reason_codes=p.reason_codes,
            )
        )

    return f_ref, p_med, out
