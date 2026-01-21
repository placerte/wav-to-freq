from __future__ import annotations

import numpy as np

from wav_to_freq.analysis.peaks.merge import (
    flag_coupled_regions,
    merge_near_duplicate_peaks,
)
from wav_to_freq.analysis.peaks.psd_peaks import find_candidate_peaks_from_psd
from wav_to_freq.domain.reason_codes import ReasonCode


def test_find_candidate_peaks_snr_gate() -> None:
    f = np.linspace(0.0, 10.0, 101)
    p = np.ones_like(f)
    p[50] = 10.0

    peaks = find_candidate_peaks_from_psd(
        f,
        p,
        fmin_hz=0.0,
        fmax_hz=10.0,
        noise_floor_percentile=50.0,
        min_peak_snr_db=6.0,
        max_candidate_peaks=5,
        is_global=True,
    )
    assert len(peaks) == 1
    assert abs(peaks[0].fi_bin_hz - 5.0) < 1e-9
    assert peaks[0].peak_snr_db is not None
    assert peaks[0].peak_snr_db > 9.0


def test_merge_near_duplicate_peaks_keeps_strongest() -> None:
    # Two very close peaks: should merge into one.
    peaks = find_candidate_peaks_from_psd(
        np.asarray([4.9, 5.0, 5.1, 5.2], dtype=np.float64),
        np.asarray([1.0, 10.0, 9.0, 1.0], dtype=np.float64),
        fmin_hz=0.0,
        fmax_hz=10.0,
        noise_floor_percentile=50.0,
        min_peak_snr_db=0.0,
        max_candidate_peaks=10,
        is_global=True,
    )
    merged = merge_near_duplicate_peaks(peaks, abs_hz=0.5, frac=0.0)
    assert len(merged) == 1
    assert abs(merged[0].fi_bin_hz - 5.0) < 1e-9


def test_flag_coupled_regions_adds_reason_codes() -> None:
    # Two peaks close enough to be flagged as coupled.
    f = np.linspace(0.0, 10.0, 101)
    p = np.ones_like(f)
    p[50] = 10.0
    p[55] = 9.0

    peaks = find_candidate_peaks_from_psd(
        f,
        p,
        fmin_hz=0.0,
        fmax_hz=10.0,
        noise_floor_percentile=50.0,
        min_peak_snr_db=0.0,
        max_candidate_peaks=10,
        is_global=True,
    )
    flagged = flag_coupled_regions(peaks, abs_hz=1.0, frac=0.0)
    assert len(flagged) >= 2
    assert ReasonCode.PSD_MULTI_PEAK in flagged[0].reason_codes
    assert ReasonCode.MULTI_MODE_SUSPECTED in flagged[0].reason_codes
