from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from scipy import signal

from wav_to_freq.analysis.modal import analyze_all_hits
from wav_to_freq.analysis.peaks.config import PeakConfig, PsdConfig
from wav_to_freq.analysis.peaks.global_peaks import compute_global_peaks
from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.domain.types import HitWindow
from wav_to_freq.io.hit_detection import prepare_hits
from wav_to_freq.reporting.plots import (
    _analysis_segment_in_window,
    _auto_psd_band,
    _pick_psd_peaks,
)


def test_free_srl2_2_hits_and_primary_frequencies() -> None:
    """Sanity test on a known multi-hit file.

    Expectations based on the archived report under:
    `examples/free_SRL2_260119/output/free_srl2_2/`
    """

    wav_path = Path("examples/free_SRL2_260119/media/audio/free srl2 2.wav")
    assert wav_path.exists(), f"Missing test WAV: {wav_path}"

    # Match the historical run conditions as closely as possible.
    stereo, windows, rep = prepare_hits(
        wav_path,
        pre_s=0.05,
        post_s=6.0,
        min_separation_s=0.30,
        threshold_sigma=8.0,
        # Historical run (archived report) used hammer = LEFT for this file.
        hammer_channel=StereoChannel.LEFT,
    )

    assert rep.n_hits_found == 10
    assert rep.n_hits_used == 10
    assert len(windows) == 10

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
    )

    assert len(results) == 10

    expected_primary_hz = 150.732421875
    primary_hz = float(results[0].fn_hz)
    assert abs(primary_hz - expected_primary_hz) < 0.01

    i0_psd, i1_psd = _analysis_segment_in_window(windows[0], results[0], stereo.fs)
    segment = np.asarray(windows[0].accel[i0_psd:i1_psd], dtype=float)
    segment = segment - float(np.mean(segment))

    nperseg = min(4096, max(256, segment.size // 2))
    f, pxx = signal.welch(segment, fs=stereo.fs, nperseg=nperseg)
    db = 10.0 * np.log10(pxx + np.finfo(float).eps)
    psd_lo, psd_hi = _auto_psd_band(
        fs=stereo.fs,
        fn_hz=results[0].fn_hz,
        fmin_default=0.5,
        fmax_default=None,
    )
    peak_idx = _pick_psd_peaks(
        f,
        db,
        n_modes=5,
        fmin_hz=psd_lo,
        fmax_hz=psd_hi,
    )

    assert len(peak_idx) >= 2, "Expected at least two PSD peaks"

    expected_secondary_hz = 86.13
    secondary_hz = float(f[peak_idx[1]])
    assert abs(secondary_hz - expected_secondary_hz) < 0.01

    settle_s = 0.010
    ring_s = 4.0
    i0 = int(round(float(settle_s) * float(stereo.fs)))
    n = int(round(float(ring_s) * float(stereo.fs)))
    windows_psd: list[HitWindow] = []
    for w in windows:
        accel = np.asarray(w.accel, dtype=np.float64)
        i1 = min(accel.size, i0 + n)
        windows_psd.append(replace(w, accel=accel[i0:i1].copy()))

    psd_cfg = PsdConfig(df_target_hz=0.25)
    peak_cfg = PeakConfig(
        noise_floor_percentile=60.0,
        min_peak_snr_db=6.0,
        max_candidate_peaks=5,
        merge_min_spacing_hz=5.0,
        merge_min_spacing_frac=0.01,
        coupled_max_spacing_hz=5.0,
        coupled_max_spacing_frac=0.01,
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
    assert any(
        abs(float(peak.fi_bin_hz) - expected_secondary_hz) < 0.01
        for peak in global_peaks
    ), "Expected 86.13 Hz in global peak list"
