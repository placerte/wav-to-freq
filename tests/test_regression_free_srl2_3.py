from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from wav_to_freq.analysis.modal import analyze_all_hits
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


def test_free_srl2_3_hits_and_primary_frequency() -> None:
    """Sanity test on a known multi-hit file.

    Expectations based on the archived report under:
    `examples/free_SRL2_260119/output/free_srl2_3/`
    """

    wav_path = Path("examples/free_SRL2_260119/media/audio/free srl2 3.wav")
    assert wav_path.exists(), f"Missing test WAV: {wav_path}"

    stereo, windows, rep = prepare_hits(
        wav_path,
        pre_s=0.05,
        post_s=6.0,
        min_separation_s=0.30,
        threshold_sigma=8.0,
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

    expected_primary_hz = 301.46484375
    assert any(
        abs(float(result.fn_hz) - expected_primary_hz) < 0.02 for result in results
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
        abs(float(peak.fi_bin_hz) - expected_primary_hz) < 0.02 for peak in global_peaks
    )
