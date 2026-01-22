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


def _find_local_max(
    f: NDArray[np.float64],
    pxx: NDArray[np.float64],
    *,
    center_hz: float,
    search_hz: float,
) -> tuple[float, float] | None:
    if f.size == 0:
        return None
    lo = float(center_hz) - float(search_hz)
    hi = float(center_hz) + float(search_hz)
    m = (f >= lo) & (f <= hi)
    if not np.any(m):
        return None
    ff = f[m]
    pp = pxx[m]
    k = int(np.argmax(pp))
    return float(ff[k]), float(pp[k])


def compute_hit_peaks(
    w: HitWindow,
    *,
    fs: float,
    fmin_hz: float,
    fmax_hz: float,
    global_peaks: list[PeakCandidate],
    psd_cfg: PsdConfig,
    peak_cfg: PeakConfig,
) -> tuple[NDArray[np.float64], NDArray[np.float64], list[PeakCandidate]]:
    """Compute per-hit candidate peaks, using global list for stability (E24)."""

    f, pxx = compute_welch_psd(
        np.asarray(w.accel, dtype=np.float64), fs=fs, cfg=psd_cfg
    )
    if f.size == 0 or pxx.size == 0:
        return np.asarray([], dtype=np.float64), np.asarray([], dtype=np.float64), []

    # 1) Start from the hit-local peak list.
    hit_candidates = find_candidate_peaks_from_psd(
        f,
        pxx,
        fmin_hz=fmin_hz,
        fmax_hz=fmax_hz,
        noise_floor_percentile=peak_cfg.noise_floor_percentile,
        min_peak_snr_db=peak_cfg.min_peak_snr_db,
        max_candidate_peaks=max(peak_cfg.max_candidate_peaks, len(global_peaks)),
        is_global=False,
    )

    # 2) Refine each global peak locally in this hit and mark it as global.
    refined_globals: list[PeakCandidate] = []
    for gp in global_peaks:
        loc = _find_local_max(
            f,
            pxx,
            center_hz=float(gp.fi_bin_hz),
            search_hz=float(peak_cfg.refine_search_hz),
        )
        if loc is None:
            continue
        fi_loc, pwr_loc = loc

        refined_globals.append(
            PeakCandidate(
                peak_rank=0,
                fi_bin_hz=fi_loc,
                fi_refined_hz=None,
                peak_power=pwr_loc,
                noise_floor=gp.noise_floor,
                peak_snr_db=gp.peak_snr_db,
                is_global=True,
                reason_codes=gp.reason_codes,
                peak_detection_count=gp.peak_detection_count,
                detection_ratio=gp.detection_ratio,
            )
        )

    # 3) Combine: prefer refined globals, then add hit-local peaks not near a global.
    combined: list[PeakCandidate] = []
    combined.extend(refined_globals)

    def _near_any_global(fi: float) -> bool:
        for g in refined_globals:
            tol = max(
                peak_cfg.merge_min_spacing_hz,
                peak_cfg.merge_min_spacing_frac * float(g.fi_bin_hz),
            )
            if abs(float(fi) - float(g.fi_bin_hz)) <= tol:
                return True
        return False

    for hc in hit_candidates:
        if _near_any_global(float(hc.fi_bin_hz)):
            continue
        combined.append(hc)

    # 4) De-dup and coupled flagging.
    combined = merge_near_duplicate_peaks(
        combined,
        abs_hz=peak_cfg.merge_min_spacing_hz,
        frac=peak_cfg.merge_min_spacing_frac,
    )
    combined = flag_coupled_regions(
        combined,
        abs_hz=peak_cfg.coupled_max_spacing_hz,
        frac=peak_cfg.coupled_max_spacing_frac,
    )

    combined.sort(key=lambda p: float(p.peak_snr_db or -1e300), reverse=True)
    combined = combined[: peak_cfg.max_candidate_peaks]

    out: list[PeakCandidate] = []
    for rank, p in enumerate(combined, start=1):
        out.append(
            PeakCandidate(
                peak_rank=rank,
                fi_bin_hz=p.fi_bin_hz,
                fi_refined_hz=p.fi_refined_hz,
                peak_power=p.peak_power,
                noise_floor=p.noise_floor,
                peak_snr_db=p.peak_snr_db,
                is_global=p.is_global,
                reason_codes=p.reason_codes,
                peak_detection_count=p.peak_detection_count,
                detection_ratio=p.detection_ratio,
            )
        )

    return f, pxx, out
