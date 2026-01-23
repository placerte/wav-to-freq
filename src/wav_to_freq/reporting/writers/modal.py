# src/wav_to_freq/reporting/writers/modal.py
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from wav_to_freq.domain.results import EstimateResult
from wav_to_freq.domain.types import HitModalResult, HitWindow
from wav_to_freq.reporting.markdown import MarkdownDoc
from wav_to_freq.reporting.sections.modal import (
    add_section_modal_summary,
    add_section_per_hit_results,
)
from wav_to_freq.utils.paths import ensure_dir
from wav_to_freq.reporting.writers.pdf import md_to_pdf


@dataclass(frozen=True)
class ModalReportArtifacts:
    report_csv: Path
    report_md: Path
    report_pdf: Path | None = None
    report_estimates_csv: Path | None = None


def write_modal_report(
    *,
    results: Sequence[HitModalResult],
    estimates: Sequence[EstimateResult] | None = None,
    out_dir: str | Path,
    fs: float,
    windows: Sequence[HitWindow],
    title: str = "Modal report",
    transient_s: float = 0.20,
    export_pdf: bool = True,
) -> ModalReportArtifacts:
    """
    Create modal artifacts:
      out_dir/
        modal_results.csv
        modal_report.md
        modal_report.pdf (optional; requires pandoc by default)
        figures/
          hits/
            ...

    If export_pdf=True and pandoc isn't installed, raises RuntimeError.
    """
    out_dir = ensure_dir(Path(out_dir))
    fig_dir = ensure_dir(out_dir / "figures")
    hits_dir = ensure_dir(fig_dir / "hits")

    # -----------------------
    # CSV
    # -----------------------
    csv_path = out_dir / "modal_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=list(asdict(results[0]).keys()) if results else []
        )
        if results:
            w.writeheader()
            for r in results:
                w.writerow(asdict(r))

    estimates_csv_path: Path | None = None
    if estimates:
        estimates_csv_path = out_dir / "modal_results_long.csv"
        with estimates_csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f, fieldnames=list(asdict(estimates[0]).keys()) if estimates else []
            )
            if estimates:
                w.writeheader()
                for e in estimates:
                    w.writerow(asdict(e))

    # -----------------------
    # Markdown
    # -----------------------
    mdd = MarkdownDoc()
    add_section_modal_summary(mdd=mdd, results=results, title=title)
    add_section_per_hit_results(
        mdd=mdd,
        windows=windows,
        results=results,
        transient_s=transient_s,
        fs=fs,
        hits_dir=hits_dir,
        out_dir=out_dir,
    )

    md_path = out_dir / "modal_report.md"
    md_path.write_text(mdd.to_markdown(), encoding="utf-8")

    pdf_path: Path | None = None
    if export_pdf:
        pdf_path = md_to_pdf(
            md_path,
            root_dir=out_dir,
            title=title,
        ).pdf_path

    return ModalReportArtifacts(
        report_csv=csv_path,
        report_md=md_path,
        report_pdf=pdf_path,
        report_estimates_csv=estimates_csv_path,
    )
