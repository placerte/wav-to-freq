from __future__ import annotations

import numpy as np

from wav_to_freq.analysis.estimators.run import compute_hit_estimates
from wav_to_freq.analysis.peaks.config import PeakConfig, PsdConfig
from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.io.hit_detection import prepare_hits


def test_compute_hit_estimates_srl2_1() -> None:
    wav_path = "examples/free_SRL2_260119/media/audio/free srl2 1.wav"
    stereo, windows, _ = prepare_hits(
        wav_path,
        pre_s=0.05,
        post_s=6.0,
        min_separation_s=0.30,
        threshold_sigma=8.0,
        hammer_channel=StereoChannel.LEFT,
    )

    estimates = compute_hit_estimates(
        windows,
        fs=stereo.fs,
        fmin_hz=50.0,
        fmax_hz=2000.0,
        psd_cfg=PsdConfig(df_target_hz=0.25),
        peak_cfg=PeakConfig(),
        settle_s=0.010,
        ring_s=1.0,
    )

    assert estimates
    assert all(e.hit_id > 0 for e in estimates)
    assert all(e.peak_rank > 0 for e in estimates)
    methods = {e.method for e in estimates}
    assert {
        "TD_ENVELOPE_FULL",
        "TD_ENVELOPE_EST",
        "FD_HALF_POWER",
        "ENERGY_ENVELOPE_SQ",
    }.issubset(methods)

    zetas = [e.zeta for e in estimates if e.zeta is not None]
    assert zetas
    assert all(np.isfinite(z) for z in zetas)
