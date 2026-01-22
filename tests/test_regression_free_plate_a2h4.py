from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from wav_to_freq.analysis.peaks.config import PeakConfig, PsdConfig
from wav_to_freq.analysis.peaks.global_peaks import compute_global_peaks
from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.domain.types import HitWindow
from wav_to_freq.io.hit_detection import prepare_hits


def _trim_windows_for_psd(
    windows: list[HitWindow], *, fs: float, settle_s: float, ring_s: float
) -> list[HitWindow]:
    out: list[HitWindow] = []
    i0 = int(round(float(settle_s) * float(fs)))
    n = int(round(float(ring_s) * float(fs)))
    for w in windows:
        accel = np.asarray(w.accel, dtype=np.float64)
        i1 = min(accel.size, i0 + n)
        out.append(replace(w, accel=accel[i0:i1].copy()))
    return out


def _assert_peak_count(
    peaks, expected_hz: float, expected_count: int, tol_hz: float = 0.3
) -> None:
    for peak in peaks:
        if abs(float(peak.fi_bin_hz) - expected_hz) <= tol_hz:
            assert peak.peak_detection_count == expected_count
            return
    raise AssertionError(f"Expected {expected_hz:.2f} Hz in global peak list")


def test_free_plate_a2h4_peak_counts() -> None:
    wav_path = Path("examples/free_plate_260122/media/audio/free_plate_A2H4.wav")
    assert wav_path.exists(), f"Missing test WAV: {wav_path}"

    stereo, windows, _ = prepare_hits(
        wav_path,
        pre_s=0.05,
        post_s=6.0,
        min_separation_s=0.30,
        threshold_sigma=8.0,
        hammer_channel=StereoChannel.LEFT,
    )

    windows_psd = _trim_windows_for_psd(
        windows, fs=stereo.fs, settle_s=0.010, ring_s=4.0
    )
    psd_cfg = PsdConfig(df_target_hz=0.25)
    peak_cfg = PeakConfig(
        noise_floor_percentile=60.0,
        min_peak_snr_db=6.0,
        max_candidate_peaks=5,
        merge_min_spacing_hz=5.0,
        merge_min_spacing_frac=0.01,
        coupled_max_spacing_hz=5.0,
        coupled_max_spacing_frac=5.0e-2,
        refine_search_hz=5.0,
    )
    _, _, global_peaks = compute_global_peaks(
        windows_psd,
        fs=stereo.fs,
        fmin_hz=50.0,
        fmax_hz=2000.0,
        psd_cfg=psd_cfg,
        peak_cfg=peak_cfg,
    )

    expected = {
        796.73: 12,
        958.23: 12,
    }
    for freq, count in expected.items():
        _assert_peak_count(global_peaks, freq, count)
