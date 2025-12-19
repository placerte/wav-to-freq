# ==== FILE: src/wav_to_freq/reporting/reporting.py ====

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Sequence

import csv
import math

from wav_to_freq.modal import HitModalResult


def write_modal_report(
    results: Sequence[HitModalResult],
    out_dir: Path | str,
    *,
    filename_csv: str = "modal_report.csv",
    filename_md: str = "modal_report.md",
) -> tuple[Path, Path]:
    """
    Writes:
      - CSV summary of modal results
      - simple Markdown summary (counts + quick stats)

    Returns: (csv_path, md_path)
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / filename_csv
    md_path = out_dir / filename_md

    # --- CSV ---
    # Use dataclasses.asdict so new fields are automatically included.
    rows = [asdict(r) for r in results]

    # Ensure stable column order with a preferred header list, then any extras.
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
        "fit_t0_s",
        "fit_t1_s",
        "reject_reason",
    ]
    all_keys = set()
    for d in rows:
        all_keys |= set(d.keys())
    extras = [k for k in sorted(all_keys) if k not in preferred]
    fieldnames = [k for k in preferred if k in all_keys] + extras

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for d in rows:
            w.writerow(d)

    # --- Markdown ---
    accepted = [r for r in results if not r.reject_reason]
    rejected = [r for r in results if r.reject_reason]

    def _finite(vals: Iterable[float]) -> list[float]:
        out: list[float] = []
        for v in vals:
            if v is None:
                continue
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                continue
            out.append(float(v))
        return out

    fn_vals = _finite(r.fn_hz for r in accepted)
    zeta_vals = _finite(r.zeta for r in accepted)

    def _mean(xs: list[float]) -> float | None:
        return (sum(xs) / len(xs)) if xs else None

    def _min(xs: list[float]) -> float | None:
        return min(xs) if xs else None

    def _max(xs: list[float]) -> float | None:
        return max(xs) if xs else None

    md_lines: list[str] = []
    md_lines.append("# Modal report")
    md_lines.append("")
    md_lines.append(f"- Total hits: **{len(results)}**")
    md_lines.append(f"- Accepted: **{len(accepted)}**")
    md_lines.append(f"- Rejected: **{len(rejected)}**")
    md_lines.append("")

    if fn_vals:
        md_lines.append("## Accepted summary")
        md_lines.append("")
        md_lines.append(
            f"- fn (Hz): mean={_mean(fn_vals):.3f}, min={_min(fn_vals):.3f}, max={_max(fn_vals):.3f}"
        )
    if zeta_vals:
        md_lines.append(
            f"- zeta: mean={_mean(zeta_vals):.6f}, min={_min(zeta_vals):.6f}, max={_max(zeta_vals):.6f}"
        )
    md_lines.append("")

    if rejected:
        md_lines.append("## Rejections (by reason)")
        md_lines.append("")
        counts: dict[str, int] = {}
        for r in rejected:
            key = r.reject_reason or "unknown"
            counts[key] = counts.get(key, 0) + 1
        for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            md_lines.append(f"- {k}: {v}")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return csv_path, md_path

