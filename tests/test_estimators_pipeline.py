from __future__ import annotations

import numpy as np

from wav_to_freq.analysis import modal
from wav_to_freq.analysis.estimators.pipeline import estimate_peak_methods
from wav_to_freq.analysis.peaks.config import PsdConfig
from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.domain.reason_codes import ReasonCode
from wav_to_freq.domain.status import EstimateStatus
from wav_to_freq.io.hit_detection import prepare_hits


def test_estimator_pipeline_srl2_1() -> None:
    wav_path = "examples/free_SRL2_260119/media/audio/free srl2 1.wav"
    stereo, windows, _ = prepare_hits(
        wav_path,
        pre_s=0.05,
        post_s=6.0,
        min_separation_s=0.30,
        threshold_sigma=8.0,
        hammer_channel=StereoChannel.LEFT,
    )

    window = windows[0]
    peak_hz = 150.732421875
    fs = stereo.fs
    start = int(round(0.010 * fs))
    end = min(window.accel.size, start + int(round(1.0 * fs)))
    segment = np.asarray(window.accel[start:end], dtype=float)
    segment = segment - float(np.mean(segment))
    y = modal._bandpass(segment, fs, peak_hz)

    estimates = estimate_peak_methods(
        y,
        hit_id=1,
        peak_rank=1,
        fs=fs,
        peak_hz=peak_hz,
        psd_cfg=PsdConfig(df_target_hz=0.25),
        coupled=False,
        peak_detection_count=13,
        total_hits=13,
        min_detection_hits=2,
        decay_min_duration_s=0.10,
        decay_min_cycles=20.0,
    )

    methods = {e.method for e in estimates}
    assert methods == {
        "TD_ENVELOPE_FULL",
        "TD_ENVELOPE_EST",
        "FD_HALF_POWER",
        "ENERGY_ENVELOPE_SQ",
    }

    for estimate in estimates:
        assert estimate.status in {
            EstimateStatus.OK,
            EstimateStatus.WARNING,
            EstimateStatus.REJECTED,
            EstimateStatus.NOT_COMPUTED,
        }

    assert any(ReasonCode.BEATING_DETECTED in e.reason_codes for e in estimates)

    fd = next(e for e in estimates if e.method == "FD_HALF_POWER")
    assert fd.zeta is not None and 0.01 <= float(fd.zeta) <= 0.6

    energy = next(e for e in estimates if e.method == "ENERGY_ENVELOPE_SQ")
    assert ReasonCode.EFFECTIVE_DAMPING_ONLY in energy.reason_codes
