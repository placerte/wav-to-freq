from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from wav_to_freq.analysis.modal import analyze_all_hits
from wav_to_freq.analysis.estimators.fd_half_power import estimate_fd_half_power
from wav_to_freq.analysis.peaks.config import PeakConfig, PsdConfig
from wav_to_freq.dsp.psd import compute_welch_psd
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


def test_free_plate_a1h3_peak_counts() -> None:
    wav_path = Path("examples/free_plate_260122/media/audio/free_plate_A1H3.wav")
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

    _assert_peak_count(global_peaks, 796.73, 13)

    results = analyze_all_hits(
        windows=windows,
        fs=stereo.fs,
        settle_s=0.010,
        ring_s=1.0,
        fmin_hz=1.0,
        fmax_hz=2000.0,
        transient_s=0.20,
        established_min_s=0.40,
        established_r2_min=0.95,
        fit_max_s=0.80,
        noise_tail_s=0.20,
        noise_mult=3.0,
        decay_min_duration_s=0.10,
        decay_min_cycles=20.0,
    )

    zetas = np.asarray([r.zeta for r in results], dtype=float)
    valid = zetas[np.isfinite(zetas)]
    assert valid.size >= 10

    zeta_mean = float(np.mean(valid))
    zeta_min = float(np.min(valid))
    zeta_max = float(np.max(valid))

    assert abs(zeta_mean - 0.000515) < 1.0e-6
    assert abs(zeta_min - 0.000443) < 1.0e-6
    assert abs(zeta_max - 0.000560) < 1.0e-6

    hp_zetas: list[float] = []
    for window, result in zip(windows, results):
        f, pxx = compute_welch_psd(
            np.asarray(window.accel, dtype=np.float64),
            fs=stereo.fs,
            cfg=psd_cfg,
        )
        hp = estimate_fd_half_power(
            f,
            pxx,
            peak_hz=result.fn_hz,
            coupled=False,
            peak_detection_count=13,
            total_hits=13,
            min_detection_hits=2,
        )
        assert not hp.reason_codes
        if np.isfinite(hp.zeta):
            hp_zetas.append(float(hp.zeta))

    assert len(hp_zetas) >= 10

    hp_mean = float(np.mean(hp_zetas))
    hp_min = float(np.min(hp_zetas))
    hp_max = float(np.max(hp_zetas))

    assert 0.04 <= hp_mean <= 0.07
    assert 0.01 <= hp_min <= 0.02
    assert 0.4 <= hp_max <= 0.6
