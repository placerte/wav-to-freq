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


def _compute_band_peaks(
    f_ref: NDArray[np.float64],
    p_med: NDArray[np.float64],
    *,
    fmin_hz: float,
    fmax_hz: float,
    noise_floor_percentile: float,
    min_peak_snr_db: float,
    max_candidate_peaks: int,
) -> list[PeakCandidate]:
    return find_candidate_peaks_from_psd(
        f_ref,
        p_med,
        fmin_hz=fmin_hz,
        fmax_hz=fmax_hz,
        noise_floor_percentile=noise_floor_percentile,
        min_peak_snr_db=min_peak_snr_db,
        max_candidate_peaks=max_candidate_peaks,
        is_global=True,
    )


def _group_hit_local_peaks(
    peaks_with_hits: list[tuple[int, PeakCandidate]],
    *,
    abs_hz: float,
    frac: float,
) -> list[tuple[PeakCandidate, set[int]]]:
    if not peaks_with_hits:
        return []

    ordered = sorted(peaks_with_hits, key=lambda item: float(item[1].fi_bin_hz))
    groups: list[tuple[PeakCandidate, set[int]]] = []

    for hit_id, peak in ordered:
        if not groups:
            groups.append((peak, {int(hit_id)}))
            continue

        rep_peak, hit_ids = groups[-1]
        ref_hz = float(rep_peak.fi_bin_hz)
        tol = max(float(abs_hz), float(frac) * ref_hz)
        if abs(float(peak.fi_bin_hz) - ref_hz) <= tol:
            hit_ids.add(int(hit_id))
            rep_snr = float(rep_peak.peak_snr_db or -1e300)
            cand_snr = float(peak.peak_snr_db or -1e300)
            if cand_snr > rep_snr:
                groups[-1] = (peak, hit_ids)
        else:
            groups.append((peak, {int(hit_id)}))

    return groups


def _collect_hit_local_groups(
    windows: list[HitWindow],
    *,
    fs: float,
    fmin_hz: float,
    fmax_hz: float,
    psd_cfg: PsdConfig,
    peak_cfg: PeakConfig,
) -> list[tuple[PeakCandidate, set[int]]]:
    noise_floor = (
        peak_cfg.hit_local_noise_floor_percentile
        if peak_cfg.hit_local_noise_floor_percentile is not None
        else peak_cfg.noise_floor_percentile
    )
    min_peak_snr = (
        peak_cfg.hit_local_min_peak_snr_db
        if peak_cfg.hit_local_min_peak_snr_db is not None
        else peak_cfg.min_peak_snr_db
    )
    max_candidates = (
        peak_cfg.hit_local_max_candidate_peaks
        if peak_cfg.hit_local_max_candidate_peaks is not None
        else peak_cfg.max_candidate_peaks
    )

    peaks_with_hits: list[tuple[int, PeakCandidate]] = []
    for w in windows:
        f, pxx = compute_welch_psd(
            np.asarray(w.accel, dtype=np.float64), fs=fs, cfg=psd_cfg
        )
        if f.size == 0 or pxx.size == 0:
            continue

        candidates = find_candidate_peaks_from_psd(
            f,
            pxx,
            fmin_hz=fmin_hz,
            fmax_hz=fmax_hz,
            noise_floor_percentile=noise_floor,
            min_peak_snr_db=min_peak_snr,
            max_candidate_peaks=max_candidates,
            is_global=False,
        )
        peaks_with_hits.extend((int(w.hit_id), peak) for peak in candidates)

        if peak_cfg.low_band_enabled:
            low_min = float(peak_cfg.low_band_min_hz)
            low_max = float(peak_cfg.low_band_max_hz)
            if low_max <= low_min:
                raise ValueError(
                    "Low-band peak settings require low_band_max_hz > low_band_min_hz"
                )
            low_noise_floor = (
                peak_cfg.low_band_noise_floor_percentile
                if peak_cfg.low_band_noise_floor_percentile is not None
                else noise_floor
            )
            low_min_peak_snr = (
                peak_cfg.low_band_min_peak_snr_db
                if peak_cfg.low_band_min_peak_snr_db is not None
                else min_peak_snr
            )
            low_max_candidates = (
                peak_cfg.low_band_max_candidate_peaks
                if peak_cfg.low_band_max_candidate_peaks is not None
                else max_candidates
            )
            low_candidates = find_candidate_peaks_from_psd(
                f,
                pxx,
                fmin_hz=low_min,
                fmax_hz=low_max,
                noise_floor_percentile=low_noise_floor,
                min_peak_snr_db=low_min_peak_snr,
                max_candidate_peaks=low_max_candidates,
                is_global=False,
            )
            peaks_with_hits.extend((int(w.hit_id), peak) for peak in low_candidates)

    return _group_hit_local_peaks(
        peaks_with_hits,
        abs_hz=peak_cfg.merge_min_spacing_hz,
        frac=peak_cfg.merge_min_spacing_frac,
    )


def _match_peak_detection_count(
    peak: PeakCandidate,
    groups: list[tuple[PeakCandidate, set[int]]],
    *,
    abs_hz: float,
    frac: float,
) -> int | None:
    if not groups:
        return None
    for rep_peak, hit_ids in groups:
        ref_hz = float(rep_peak.fi_bin_hz)
        tol = max(float(abs_hz), float(frac) * ref_hz)
        if abs(float(peak.fi_bin_hz) - ref_hz) <= tol:
            return len(hit_ids)
    return None


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

    peaks = _compute_band_peaks(
        f_ref,
        p_med,
        fmin_hz=fmin_hz,
        fmax_hz=fmax_hz,
        noise_floor_percentile=peak_cfg.noise_floor_percentile,
        min_peak_snr_db=peak_cfg.min_peak_snr_db,
        max_candidate_peaks=peak_cfg.max_candidate_peaks,
    )

    if peak_cfg.low_band_enabled:
        low_min = float(peak_cfg.low_band_min_hz)
        low_max = float(peak_cfg.low_band_max_hz)
        if low_max <= low_min:
            raise ValueError(
                "Low-band peak settings require low_band_max_hz > low_band_min_hz"
            )
        low_noise_floor = (
            peak_cfg.low_band_noise_floor_percentile
            if peak_cfg.low_band_noise_floor_percentile is not None
            else peak_cfg.noise_floor_percentile
        )
        low_min_peak_snr = (
            peak_cfg.low_band_min_peak_snr_db
            if peak_cfg.low_band_min_peak_snr_db is not None
            else peak_cfg.min_peak_snr_db
        )
        low_max_candidates = (
            peak_cfg.low_band_max_candidate_peaks
            if peak_cfg.low_band_max_candidate_peaks is not None
            else peak_cfg.max_candidate_peaks
        )
        low_peaks = _compute_band_peaks(
            f_ref,
            p_med,
            fmin_hz=low_min,
            fmax_hz=low_max,
            noise_floor_percentile=low_noise_floor,
            min_peak_snr_db=low_min_peak_snr,
            max_candidate_peaks=low_max_candidates,
        )
        peaks.extend(low_peaks)

    hit_local_groups: list[tuple[PeakCandidate, set[int]]] = []
    total_hits = len(windows)
    if peak_cfg.hit_local_enabled:
        hit_local_groups = _collect_hit_local_groups(
            windows,
            fs=fs,
            fmin_hz=fmin_hz,
            fmax_hz=fmax_hz,
            psd_cfg=psd_cfg,
            peak_cfg=peak_cfg,
        )
        min_hits = max(1, int(peak_cfg.hit_local_min_hits))
        for peak, hit_ids in hit_local_groups:
            if len(hit_ids) < min_hits:
                continue
            peaks.append(
                PeakCandidate(
                    peak_rank=0,
                    fi_bin_hz=peak.fi_bin_hz,
                    fi_refined_hz=peak.fi_refined_hz,
                    peak_power=peak.peak_power,
                    noise_floor=peak.noise_floor,
                    peak_snr_db=peak.peak_snr_db,
                    is_global=True,
                    reason_codes=peak.reason_codes,
                    peak_detection_count=len(hit_ids),
                    detection_ratio=len(hit_ids) / total_hits if total_hits else None,
                )
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
        peak_detection_count = _match_peak_detection_count(
            p,
            hit_local_groups,
            abs_hz=peak_cfg.merge_min_spacing_hz,
            frac=peak_cfg.merge_min_spacing_frac,
        )
        detection_ratio = (
            peak_detection_count / total_hits
            if peak_detection_count is not None and total_hits
            else None
        )
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
                peak_detection_count=peak_detection_count,
                detection_ratio=detection_ratio,
            )
        )

    return f_ref, p_med, out
