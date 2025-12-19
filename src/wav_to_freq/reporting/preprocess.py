from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from wav_to_freq.impact_io import StereoWav, HitWindow, HitDetectionReport
from wav_to_freq.other_utils import ensure_dir
from wav_to_freq.reporting.context import PreprocessContext
from wav_to_freq.reporting.markdown import MarkdownDoc
from wav_to_freq.reporting.plots import plot_overview_two_channels
from wav_to_freq.reporting.sections import add_section_wav_specs


@dataclass(frozen=True)
class PreprocessReportArtifacts:
    report_md: Path

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
          hammer_with_hits.png
    """
    out_dir = ensure_dir(Path(out_dir))
    fig_dir = ensure_dir(out_dir / "figures")

    fig_overview = plot_overview_two_channels(
    stereo,
    windows,
    fig_dir / "overview_two_channels.png",
    max_seconds=max_plot_seconds,
)

    mdd = MarkdownDoc()
    mdd.h1(title)

    context: PreprocessContext = PreprocessContext(
        out_dir=out_dir,
        fig_dir=fig_dir,
        stereo=stereo,
        windows=windows,
        hit_report=report,
        title=title,
        max_plot_seconds=max_plot_seconds,
        )
    
    add_section_wav_specs(mdd=mdd, context=context)

    # Section: Hit detection summary
    mdd.h2("Hit detection summary")
    mdd.table(
        headers=["Metric", "Value"],
        rows=[
            ["Hits found", str(int(report.n_hits_found))],
            ["Hits used", str(int(report.n_hits_used))],
            ["Threshold (abs)", f"{float(report.threshold):.6g}"],
            ["Min separation (s)", f"{float(report.min_separation_s):.6g}"],
            ["Window pre (s)", f"{float(report.pre_s):.6g}"],
            ["Window post (s)", f"{float(report.post_s):.6g}"],
        ],
    )


    # Section: Raw parameters (nice for traceability)
    mdd.h2("Raw parameters (traceability)")
    mdd.codeblock(
        "\n".join(
            [
                f"hammer_channel={stereo.hammer_channel!r}",
                f"n_hits_found={report.n_hits_found}",
                f"n_hits_used={report.n_hits_used}",
                f"threshold={report.threshold}",
                f"min_separation_s={report.min_separation_s}",
                f"pre_s={report.pre_s}",
                f"post_s={report.post_s}",
            ]
        ),
        lang="text",
    )

    mdd.p("Overview (hammer on top, response on bottom), aligned in time:")
    mdd.add(f"![overview two channels]({fig_overview.relative_to(out_dir).as_posix()})")
    mdd.add()

    report_md = out_dir / "report_preprocess.md"
    report_md.write_text(mdd.to_markdown(), encoding="utf-8")

    return PreprocessReportArtifacts(
        report_md=report_md,
    )
