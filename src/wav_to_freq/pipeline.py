# ==== FILE: src/wav_to_freq/pipeline.py ====
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wav_to_freq.analysis.estimators.run import compute_hit_estimates
from wav_to_freq.analysis.modal import analyze_all_hits
from wav_to_freq.analysis.peaks.config import PeakConfig, PsdConfig
from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.io.hit_detection import prepare_hits
from wav_to_freq.reporting.writers.modal import ModalReportArtifacts, write_modal_report
from wav_to_freq.reporting.writers.preprocess import (
    PreprocessReportArtifacts,
    write_preprocess_report,
)


@dataclass(frozen=True)
class PipelineArtifacts:
    out_dir: Path

    # preprocessing
    preprocess: PreprocessReportArtifacts

    # modal report
    modal: ModalReportArtifacts


def run_full_report(
    wav_path: str | Path,
    *,
    out_dir: str | Path,
    hammer_channel: StereoChannel = StereoChannel.UNKNOWN,
    # ----------------------------
    # Hit detection / extraction
    # ----------------------------
    pre_s: float = 0.05,
    post_s: float = 1.50,
    min_separation_s: float = 0.30,
    threshold_sigma: float = 8.0,
    # ----------------------------
    # Modal analysis (frequency band)
    # ----------------------------
    fmin_hz: float = 1.0,
    fmax_hz: float = 2000.0,
    # ----------------------------
    # Modal analysis (time/window knobs)
    # ----------------------------
    settle_s: float = 0.010,
    ring_s: float = 1.0,
    # damping / established-zone knobs
    transient_s: float = 0.20,
    established_min_s: float = 0.40,
    established_r2_min: float = 0.95,
    fit_max_s: float = 0.80,
    noise_tail_s: float = 0.20,
    noise_mult: float = 3.0,
    # ----------------------------
    # Reporting
    # ----------------------------
    title_preprocess: str = "WAV preprocessing report",
    title_modal: str = "Modal report",
    max_plot_seconds: float | None = None,
    export_pdf: bool = True,
) -> PipelineArtifacts:
    """
    One-call end-to-end report generator.

    Pipeline:
      prepare_hits -> write_preprocess_report -> analyze_all_hits -> write_modal_report
    """
    wav_path = Path(wav_path)
    out_dir = Path(out_dir)

    stereo, windows, rep = prepare_hits(
        wav_path,
        pre_s=pre_s,
        post_s=post_s,
        min_separation_s=min_separation_s,
        threshold_sigma=threshold_sigma,
        hammer_channel=hammer_channel,
    )

    preprocess = write_preprocess_report(
        out_dir,
        stereo=stereo,
        windows=windows,
        report=rep,
        title=title_preprocess,
        max_plot_seconds=max_plot_seconds,
    )

    results = analyze_all_hits(
        windows=windows,
        fs=stereo.fs,
        settle_s=settle_s,
        ring_s=ring_s,
        fmin_hz=fmin_hz,
        fmax_hz=fmax_hz,
        transient_s=transient_s,
        established_min_s=established_min_s,
        established_r2_min=established_r2_min,
        fit_max_s=fit_max_s,
        noise_tail_s=noise_tail_s,
        noise_mult=noise_mult,
    )

    estimates = compute_hit_estimates(
        windows,
        fs=stereo.fs,
        fmin_hz=fmin_hz,
        fmax_hz=fmax_hz,
        psd_cfg=PsdConfig(df_target_hz=0.25),
        peak_cfg=PeakConfig(),
        settle_s=settle_s,
        ring_s=ring_s,
        transient_s=transient_s,
        established_min_s=established_min_s,
        established_r2_min=established_r2_min,
        fit_max_s=fit_max_s,
        noise_tail_s=noise_tail_s,
        noise_mult=noise_mult,
    )

    modal = write_modal_report(
        results=results,
        estimates=estimates,
        out_dir=out_dir,
        windows=windows,
        fs=stereo.fs,
        title=title_modal,
        export_pdf=export_pdf,
    )

    return PipelineArtifacts(out_dir=out_dir, preprocess=preprocess, modal=modal)
