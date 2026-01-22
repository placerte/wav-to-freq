from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.signal import find_peaks

from wav_to_freq.analysis.peaks.noise_floor import compute_noise_floor_percentile
from wav_to_freq.domain.reason_codes import ReasonCode
from wav_to_freq.domain.results import PeakCandidate


def _snr_db(peak_power: float, noise_floor: float) -> float:
    eps = np.finfo(float).tiny
    return float(
        10.0 * np.log10((float(peak_power) + eps) / (float(noise_floor) + eps))
    )


def find_candidate_peaks_from_psd(
    f_hz: NDArray[np.float64],
    pxx: NDArray[np.float64],
    *,
    fmin_hz: float,
    fmax_hz: float,
    noise_floor_percentile: float,
    min_peak_snr_db: float,
    max_candidate_peaks: int,
    is_global: bool,
) -> list[PeakCandidate]:
    """Detect and rank peaks in a PSD (E26/E27).

    v1 baseline:

    - Compute a band-limited noise floor percentile.
    - Compute peak SNR in dB relative to that floor.
    - Keep up to N peaks passing the SNR threshold.
    """

    f = np.asarray(f_hz, dtype=np.float64)
    p = np.asarray(pxx, dtype=np.float64)
    if f.size == 0 or p.size == 0 or f.size != p.size:
        return []

    band = (f >= float(fmin_hz)) & (f <= float(fmax_hz))
    if not np.any(band):
        return []

    fb = f[band]
    pb = p[band]
    noise_floor = compute_noise_floor_percentile(pb, percentile=noise_floor_percentile)
    if not np.isfinite(noise_floor):
        return []

    peak_idx, _ = find_peaks(pb)

    candidates: list[PeakCandidate] = []
    for i in peak_idx:
        fi = float(fb[int(i)])
        peak_power = float(pb[int(i)])
        snr_db = _snr_db(peak_power, noise_floor)

        if snr_db < float(min_peak_snr_db):
            continue

        candidates.append(
            PeakCandidate(
                peak_rank=0,
                fi_bin_hz=fi,
                fi_refined_hz=None,
                peak_power=peak_power,
                noise_floor=noise_floor,
                peak_snr_db=snr_db,
                is_global=bool(is_global),
                reason_codes=(),
                peak_detection_count=None,
                detection_ratio=None,
            )
        )

    # rank by descending SNR
    candidates.sort(key=lambda c: float(c.peak_snr_db or -1e300), reverse=True)
    candidates = candidates[: max(0, int(max_candidate_peaks))]

    # assign rank
    for rank, c in enumerate(candidates, start=1):
        candidates[rank - 1] = PeakCandidate(
            peak_rank=rank,
            fi_bin_hz=c.fi_bin_hz,
            fi_refined_hz=c.fi_refined_hz,
            peak_power=c.peak_power,
            noise_floor=c.noise_floor,
            peak_snr_db=c.peak_snr_db,
            is_global=c.is_global,
            reason_codes=c.reason_codes,
            peak_detection_count=c.peak_detection_count,
            detection_ratio=c.detection_ratio,
        )

    if not candidates:
        # No candidates passing threshold; callers may attach NO_VALID_PEAKS/SNR_LOW.
        return []

    return candidates


def attach_no_valid_peaks_reason(hit_id: int) -> PeakCandidate:
    """Utility for callers that want to represent 'no valid peaks' explicitly."""

    return PeakCandidate(
        peak_rank=0,
        fi_bin_hz=float("nan"),
        fi_refined_hz=None,
        peak_power=None,
        noise_floor=None,
        peak_snr_db=None,
        is_global=False,
        reason_codes=(ReasonCode.NO_VALID_PEAKS, ReasonCode.SNR_LOW),
        peak_detection_count=None,
        detection_ratio=None,
    )
