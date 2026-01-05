# ==== FILE: src/wav_to_freq/reporting/reporting.py ====
from __future__ import annotations

import csv
import math
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Sequence

from wav_to_freq.impact_io import HitWindow
from wav_to_freq.modal import HitModalResult
from wav_to_freq.other_utils import ensure_dir
from wav_to_freq.reporting.markdown import MarkdownDoc
from wav_to_freq.reporting.plots import plot_hit_response_report


def _finite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _fmt(x: float | None, fmt: str) -> str:
    if x is None or not _finite(x):
        return ""
    return format(float(x), fmt)


def _mean(xs: list[float]) -> float | None:
    return (sum(xs) / len(xs)) if xs else None


def _min(xs: list[float]) -> float | None:
    return min(xs) if xs else None


def _max(xs: list[float]) -> float | None:
    return max(xs) if xs else None


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
    accepted = [r for r in results if not r.reject_reason]
    rejected = [r for r in results if r.reject_reason]

    fn_vals = [float(r.fn_hz) for r in accepted if _finite(r.fn_hz)]
    zeta_vals = [float(r.zeta) for r in accepted if _finite(r.zeta)]
    snr_vals = [float(r.snr_db) for r in accepted if _finite(r.snr_db)]
    r2_vals = [float(r.env_fit_r2) for r in accepted if _finite(r.env_fit_r2)]

    mdd = MarkdownDoc()
    mdd.h1(title)

    mdd.bullet(
        [
            f"Total hits: **{len(results)}**",
            f"Accepted: **{len(accepted)}**",
            f"Rejected: **{len(rejected)}**",
        ]
    )

    if accepted:
        mdd.h2("Accepted summary")
        items: list[str] = []
        if fn_vals:
            items.append(
                f"fn (Hz): mean={_fmt(_mean(fn_vals), '.3f')}, min={_fmt(_min(fn_vals), '.3f')}, max={_fmt(_max(fn_vals), '.3f')}"
            )
        if zeta_vals:
            items.append(
                f"zeta: mean={_fmt(_mean(zeta_vals), '.6f')}, min={_fmt(_min(zeta_vals), '.6f')}, max={_fmt(_max(zeta_vals), '.6f')}"
            )
        if snr_vals:
            items.append(
                f"SNR (dB): mean={_fmt(_mean(snr_vals), '.2f')}, min={_fmt(_min(snr_vals), '.2f')}, max={_fmt(_max(snr_vals), '.2f')}"
            )
        if r2_vals:
            items.append(
                f"Envelope fit R²: mean={_fmt(_mean(r2_vals), '.3f')}, min={_fmt(_min(r2_vals), '.3f')}, max={_fmt(_max(r2_vals), '.3f')}"
            )
        mdd.bullet(items)

    if rejected:
        mdd.h2("Rejections (by reason)")
        counts: dict[str, int] = {}
        for r in rejected:
            key = r.reject_reason or "unknown"
            counts[key] = counts.get(key, 0) + 1
        mdd.bullet([f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))])

    # -----------------------
    # Per-hit section + figures
    # -----------------------
    mdd.h2("Hit-by-hit")

    n = min(len(windows), len(results))
    for i in range(n):
        w = windows[i]
        r = results[i]

        label = f"H{int(r.hit_id):03d}"
        out_png = hits_dir / f"{label}_response.png"

        plot_hit_response_report(
            fs=fs,
            window=w,
            result=r,
            out_png=out_png,
            transient_s=transient_s,
        )

        mdd.h3(label)
        mdd.bullet(
            [
                f"fn={_fmt(float(r.fn_hz), '.3f')} Hz",
                f"zeta={_fmt(float(r.zeta), '.6f')}",
                f"SNR={_fmt(float(r.snr_db), '.2f')} dB",
                f"R²={_fmt(float(r.env_fit_r2), '.3f')}",
            ]
            + ([f"reject_reason: `{r.reject_reason}`"] if r.reject_reason else [])
        )
        mdd.image(out_png.relative_to(out_dir).as_posix(), alt=f"{label} response")

    md_path = out_dir / "modal_report.md"
    md_path.write_text(mdd.to_markdown(), encoding="utf-8")

    return csv_path, md_path

