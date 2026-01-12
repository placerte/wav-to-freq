from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wav_to_freq.analysis.modal import analyze_all_hits
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
    # hit detection / windowing
    pre_s: float = 0.05,
    post_s: float = 1.50,
    min_separation_s: float = 0.30,
    threshold_sigma: float = 8.0,
    # modal analysis
    fmin_hz: float = 1.0,
    fmax_hz: float = 2000.0,
    # reporting
    title_preprocess: str = "WAV preprocessing report",
    title_modal: str = "Modal report",
    max_plot_seconds: float | None = None,
) -> PipelineArtifacts:
    """
    One-call end-to-end report generator.

    This is essentially scripts/dev_check.py turned into a reusable function:
      prepare_hits -> write_preprocess_report -> analyze_all_hits -> write_modal_report.
    """
    wav_path = Path(wav_path)
    out_dir = Path(out_dir)

    stereo, windows, rep = prepare_hits(
        wav_path,
        pre_s=pre_s,
        post_s=post_s,
        min_separation_s=min_separation_s,
        threshold_sigma=threshold_sigma,
        # hammer_channel override intentionally left out (auto by default)
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
        fmin_hz=fmin_hz,
        fmax_hz=fmax_hz,
    )

    modal = write_modal_report(
        results=results,
        out_dir=out_dir,
        windows=windows,
        fs=stereo.fs,
        title=title_modal,
    )

    return PipelineArtifacts(
        out_dir=out_dir,
        preprocess=preprocess,
        modal=modal
    )

