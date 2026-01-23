from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from wav_to_freq.analysis.estimators.pipeline import estimate_peak_methods
from wav_to_freq.analysis.peaks.config import PeakConfig, PsdConfig
from wav_to_freq.analysis.peaks.global_peaks import compute_global_peaks
from wav_to_freq.analysis.peaks.per_hit_peaks import compute_hit_peaks
from wav_to_freq.domain.results import EstimateResult
from wav_to_freq.domain.types import HitWindow
from wav_to_freq.analysis import modal


def compute_hit_estimates(
    windows: Sequence[HitWindow],
    *,
    fs: float,
    fmin_hz: float,
    fmax_hz: float,
    psd_cfg: PsdConfig,
    peak_cfg: PeakConfig,
    settle_s: float = 0.010,
    ring_s: float = 1.0,
    transient_s: float = 0.20,
    established_min_s: float = 0.40,
    established_r2_min: float = 0.95,
    fit_max_s: float = 0.80,
    noise_tail_s: float = 0.20,
    noise_mult: float = 3.0,
    decay_min_duration_s: float = 1.0,
    decay_min_cycles: float = 8.0,
    beating_score_max: float = 0.20,
    envelope_increase_frac_max: float = 0.10,
    inst_freq_rel_jitter_max: float = 0.05,
    filter_q_factor_max: float = 5.0,
) -> list[EstimateResult]:
    windows_psd = _trim_windows_for_psd(
        windows, fs=fs, settle_s=settle_s, ring_s=ring_s
    )
    _, _, global_peaks = compute_global_peaks(
        windows_psd,
        fs=fs,
        fmin_hz=fmin_hz,
        fmax_hz=fmax_hz,
        psd_cfg=psd_cfg,
        peak_cfg=peak_cfg,
    )

    total_hits = len(windows)
    estimates: list[EstimateResult] = []
    for window in windows:
        f, pxx, peaks = compute_hit_peaks(
            window,
            fs=fs,
            fmin_hz=fmin_hz,
            fmax_hz=fmax_hz,
            global_peaks=global_peaks,
            psd_cfg=psd_cfg,
            peak_cfg=peak_cfg,
        )
        if not peaks:
            continue

        start = int(round(settle_s * float(fs)))
        end = min(window.accel.size, start + int(round(ring_s * float(fs))))
        segment = np.asarray(window.accel[start:end], dtype=np.float64)
        if segment.size == 0:
            continue
        segment = segment - float(np.mean(segment))

        for peak in peaks:
            y = modal._bandpass(segment, float(fs), float(peak.fi_bin_hz))
            estimates.extend(
                estimate_peak_methods(
                    y,
                    hit_id=int(window.hit_id),
                    peak_rank=int(peak.peak_rank),
                    fs=float(fs),
                    peak_hz=float(peak.fi_bin_hz),
                    psd_cfg=psd_cfg,
                    coupled=any(
                        code.value in {"PSD_MULTI_PEAK", "MULTI_MODE_SUSPECTED"}
                        for code in peak.reason_codes
                    ),
                    peak_detection_count=peak.peak_detection_count,
                    total_hits=total_hits,
                    min_detection_hits=2,
                    transient_s=transient_s,
                    established_min_s=established_min_s,
                    established_r2_min=established_r2_min,
                    fit_max_s=fit_max_s,
                    noise_tail_s=noise_tail_s,
                    noise_mult=noise_mult,
                    decay_min_duration_s=decay_min_duration_s,
                    decay_min_cycles=decay_min_cycles,
                    beating_score_max=beating_score_max,
                    envelope_increase_frac_max=envelope_increase_frac_max,
                    inst_freq_rel_jitter_max=inst_freq_rel_jitter_max,
                    filter_q_factor_max=filter_q_factor_max,
                )
            )

    return estimates


def _trim_windows_for_psd(
    windows: Sequence[HitWindow], *, fs: float, settle_s: float, ring_s: float
) -> list[HitWindow]:
    out: list[HitWindow] = []
    i0 = int(round(float(settle_s) * float(fs)))
    n = int(round(float(ring_s) * float(fs)))
    for w in windows:
        accel = np.asarray(w.accel, dtype=np.float64)
        i1 = min(accel.size, i0 + n)
        out.append(
            HitWindow(
                hit_id=w.hit_id,
                hit_index=w.hit_index,
                t_hit=w.t_hit,
                t_start=w.t_start,
                t_end=w.t_end,
                hammer=w.hammer,
                accel=accel[i0:i1].copy(),
            )
        )
    return out
