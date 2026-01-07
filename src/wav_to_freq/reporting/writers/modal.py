from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from wav_to_freq.domain.types import HitModalResult, HitWindow
from wav_to_freq.reporting.sections.modal import add_section_per_hit_results, add_section_modal_summary
from wav_to_freq.utils.paths import ensure_dir
from wav_to_freq.reporting.markdown import MarkdownDoc


def write_modal_report(
    *,
    results: Sequence[HitModalResult],
    out_dir: str | Path,
    fs: float,
    windows: Sequence[HitWindow],
    title: str = "Modal report",
    transient_s: float = 0.20,
) -> tuple[Path, Path]:
    """
    Non-breaking signature (matches your smoke_test usage):
      write_modal_report(results=..., out_dir=..., fs=..., windows=..., title=...)

    Outputs:
      out_dir/
        modal_report.csv
        modal_report.md
        figures/
          hits/
            H001_response.png
            H002_response.png
            ...
    """
    out_dir = ensure_dir(Path(out_dir))
    fig_dir = ensure_dir(out_dir / "figures")
    hits_dir = ensure_dir(fig_dir / "hits")

    fs = float(fs)

    # -----------------------
    # CSV
    # -----------------------
    csv_path = out_dir / "modal_report.csv"
    rows = [asdict(r) for r in results]

    preferred = [
        "hit_id",
        "hit_index",
        "t0_s",
        "t1_s",
        "fn_hz",
        "zeta",
        "snr_db",
        "env_fit_r2",
        "env_log_c",
        "env_log_m",
        "reject_reason",
        # optional future fields (ok if absent)
        "fit_t0_s",
        "fit_t1_s",
    ]
    extra_cols = sorted({k for d in rows for k in d.keys()} - set(preferred))
    fieldnames = [c for c in preferred if any(c in d for d in rows)] + extra_cols

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for d in rows:
            w.writerow(d)

    # -----------------------
    # Markdown
    # -----------------------

    mdd = MarkdownDoc()

    add_section_modal_summary(mdd=mdd,results=results,title=title)
    add_section_per_hit_results(mdd=mdd,windows=windows, results=results, transient_s=transient_s, fs=fs, hits_dir=hits_dir,out_dir=out_dir)

    md_path = out_dir / "modal_report.md"
    md_path.write_text(mdd.to_markdown(), encoding="utf-8")

    return csv_path, md_path
