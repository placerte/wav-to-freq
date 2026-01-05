# ==== FILE: src/wav_to_freq/reporting/reporting.py ====
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Sequence

import csv
import math

from wav_to_freq.impact_io import HitWindow
from wav_to_freq.modal import HitModalResult
from wav_to_freq.reporting.plots import plot_hit_response_report


def _finite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _fmt(x: float | None, fmt: str) -> str:
    if x is None or not _finite(x):
        return ""
    return format(float(x), fmt)


def _mean(vals: list[float]) -> float | None:
    return (sum(vals) / len(vals)) if vals else None


def _min(vals: list[float]) -> float | None:
    return min(vals) if vals else None


def _max(vals: list[float]) -> float | None:
    return max(vals) if vals else None


def _hit_label(hit_id: int) -> str:
    return f"H{hit_id:03d}"


def write_modal_report(
    *,
    results: Sequence[HitModalResult],
    out_dir: str | Path,
    fs: float,
    windows: Sequence[HitWindow],
    title: str = "Modal report",
    transient_s: float = 0.2,
) -> tuple[Path, Path]:
    """
    Writes:
      - modal_report.csv (all hits)
      - modal_report.md (summary + per-hit figures)
    Generates:
      - out_dir/figures/hits/H###_response.png

    IMPORTANT:
      - This version does NOT require HitWindow.i0/i1.
      - It plots directly from HitWindow.accel and time stamps.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    hits_dir = fig_dir / "hits"
    hits_dir.mkdir(parents=True, exist_ok=True)

    fs = float(fs)

    # ---------------------------------------------------------------------
    # 1) CSV
    # ---------------------------------------------------------------------
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
        # optional if present in your HitModalResult:
        "fit_t0_s",
        "fit_t1_s",
        "fit_i0",
        "fit_i1",
    ]
    extra_cols = sorted({k for d in rows for k in d.keys()} - set(preferred))
    headers = [c for c in preferred if any(c in d for d in rows)] + extra_cols

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for d in rows:
            w.writerow(d)

    # ---------------------------------------------------------------------
    # 2) Markdown summary
    # ---------------------------------------------------------------------
    md_path = out_dir / "modal_report.md"

    accepted: list[HitModalResult] = []
    rejected: list[HitModalResult] = []
    for r in results:
        if r.reject_reason:
            rejected.append(r)
        else:
            accepted.append(r)

    fn_vals = [float(r.fn_hz) for r in accepted if _finite(r.fn_hz)]
    zeta_vals = [float(r.zeta) for r in accepted if _finite(r.zeta)]
    snr_vals = [float(r.snr_db) for r in accepted if _finite(r.snr_db)]
    r2_vals = [float(r.env_fit_r2) for r in accepted if _finite(r.env_fit_r2)]

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- Total hits: **{len(results)}**")
    lines.append(f"- Accepted: **{len(accepted)}**")
    lines.append(f"- Rejected: **{len(rejected)}**")
    lines.append("")

    if accepted:
        lines.append("## Accepted summary")
        lines.append("")
        if fn_vals:
            lines.append(
                f"- fn (Hz): mean={_fmt(_mean(fn_vals), '.3f')}, "
                f"min={_fmt(_min(fn_vals), '.3f')}, max={_fmt(_max(fn_vals), '.3f')}"
            )
        if zeta_vals:
            lines.append(
                f"- zeta: mean={_fmt(_mean(zeta_vals), '.6f')}, "
                f"min={_fmt(_min(zeta_vals), '.6f')}, max={_fmt(_max(zeta_vals), '.6f')}"
            )
        if snr_vals:
            lines.append(
                f"- SNR (dB): mean={_fmt(_mean(snr_vals), '.2f')}, "
                f"min={_fmt(_min(snr_vals), '.2f')}, max={_fmt(_max(snr_vals), '.2f')}"
            )
        if r2_vals:
            lines.append(
                f"- Envelope fit R²: mean={_fmt(_mean(r2_vals), '.3f')}, "
                f"min={_fmt(_min(r2_vals), '.3f')}, max={_fmt(_max(r2_vals), '.3f')}"
            )
        lines.append("")

    if rejected:
        lines.append("## Rejections (by reason)")
        lines.append("")
        counts: dict[str, int] = {}
        for r in rejected:
            counts[r.reject_reason] = counts.get(r.reject_reason, 0) + 1
        for reason, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- {reason}: {count}")
        lines.append("")

    # ---------------------------------------------------------------------
    # 3) Per-hit figures + hit-by-hit section 
    # ---------------------------------------------------------------------
    # We assume 1:1 ordering between windows and results (hit 1 ↔ window 1, etc.)
    # If you later want key-based matching, do it explicitly (no getattr fishing).
    n = min(len(windows), len(results))

    lines.append("## Hit-by-hit")
    lines.append("")
    lines.append(
        "Each section includes a per-hit response plot (raw window, bandpass at fn, transient/established shading, "
        "and envelope fit on established zone)."
    )
    lines.append("")

    for i in range(n):
        w = windows[i]
        r = results[i]

        # Determine hit id consistently:
        # Prefer r.hit_id (your model), else fall back to 1-based order.
        hit_id = int(getattr(r, "hit_id", i + 1))
        label = _hit_label(hit_id)

        out_png = hits_dir / f"{label}_response.png"
        plot_hit_response_report(
            fs=fs,
            window=w,
            result=r,
            out_png=out_png,
            transient_s=transient_s,
        )

        lines.append(f"### {label}")
        lines.append("")
        lines.append(
            f"- fn={_fmt(float(r.fn_hz), '.3f')} Hz, "
            f"zeta={_fmt(float(r.zeta), '.6f')}, "
            f"SNR={_fmt(float(r.snr_db), '.2f')} dB, "
            f"R²={_fmt(float(r.env_fit_r2), '.3f')}"
        )
        if r.reject_reason:
            lines.append(f"- reject_reason: `{r.reject_reason}`")
        lines.append("")
        lines.append(f"![{label} response]({out_png.relative_to(out_dir).as_posix()})")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, md_path

