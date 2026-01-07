# ==== FILE: src/wav_to_freq/reporting/preprocess.py ====

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from wav_to_freq.domain.types import HitDetectionReport, HitWindow, StereoWav
from wav_to_freq.utils.paths import ensure_dir
from wav_to_freq.reporting.context import PreprocessContext
from wav_to_freq.reporting.markdown import MarkdownDoc
from wav_to_freq.reporting.plots import plot_overview_two_channels
from wav_to_freq.reporting.sections.preprocess import add_section_wav_specs


@dataclass(frozen=True)
class PreprocessReportArtifacts:
    report_md: Path
    fig_overview: Path


def write_preprocess_report(
    out_dir: str | Path,
    *,
    stereo: StereoWav,
    windows: Sequence[HitWindow],
    report: HitDetectionReport,
    title: str = "WAV preprocessing report",
    max_plot_seconds: float | None = None,
) -> PreprocessReportArtifacts:
    """
    Create a markdown report + figures for the preprocessing stage.

    Output structure:
      out_dir/
        report_preprocess.md
        figures/
          overview_two_channels.png
    """
    out_dir = ensure_dir(Path(out_dir))
    fig_dir = ensure_dir(out_dir / "figures")

    fig_overview = plot_overview_two_channels(
        stereo,
        list(windows),
        fig_dir / "overview_two_channels.png",
        max_seconds=max_plot_seconds,
    )

    mdd = MarkdownDoc()
    mdd.h1(title)

    context = PreprocessContext(
        out_dir=out_dir,
        fig_dir=fig_dir,
        stereo=stereo,
        windows=windows,
        hit_report=report,
        title=title,
        max_plot_seconds=max_plot_seconds,
    )

    add_section_wav_specs(mdd=mdd, context=context)

    mdd.h2("Overview")
    mdd.p("Overview (hammer on top, response on bottom), aligned in time:")
    mdd.image(fig_overview.relative_to(out_dir).as_posix(), alt="overview two channels")

    report_md = out_dir / "report_preprocess.md"
    report_md.write_text(mdd.to_markdown(), encoding="utf-8")

    return PreprocessReportArtifacts(report_md=report_md, fig_overview=fig_overview)
