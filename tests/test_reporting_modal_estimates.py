from __future__ import annotations

from pathlib import Path

from wav_to_freq.analysis.estimators.run import compute_hit_estimates
from wav_to_freq.analysis.modal import analyze_all_hits
from wav_to_freq.analysis.peaks.config import PeakConfig, PsdConfig
from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.io.hit_detection import prepare_hits
from wav_to_freq.reporting.writers.modal import write_modal_report


def test_modal_report_writes_estimates_csv(tmp_path: Path) -> None:
    wav_path = "examples/free_SRL2_260119/media/audio/free srl2 1.wav"
    stereo, windows, _ = prepare_hits(
        wav_path,
        pre_s=0.05,
        post_s=6.0,
        min_separation_s=0.30,
        threshold_sigma=8.0,
        hammer_channel=StereoChannel.LEFT,
    )

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

    artifacts = write_modal_report(
        results=results,
        estimates=estimates,
        out_dir=tmp_path,
        windows=windows,
        fs=stereo.fs,
        export_pdf=False,
    )

    assert artifacts.report_estimates_csv is not None
    assert artifacts.report_estimates_csv.exists()
    assert artifacts.report_md.exists()
    report_text = artifacts.report_md.read_text(encoding="utf-8")
    assert "Hit Summary" in report_text
