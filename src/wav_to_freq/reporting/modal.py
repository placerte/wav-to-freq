from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from wav_to_freq.impact_io import StereoWav, HitWindow, HitDetectionReport
from wav_to_freq.modal import HitModalResult
from wav_to_freq.other_utils import ensure_dir
from wav_to_freq.reporting.markdown import MarkdownDoc
from wav_to_freq.reporting.plots import plot_hit_response_with_damping, plot_hit_spectrum


@dataclass(frozen=True)
class ModalReportArtifacts:
    report_md: Path


def write_modal_report(
    *,
    out_dir: Path,
    stereo: StereoWav,
    windows: Sequence[HitWindow],
    hit_report: HitDetectionReport,
    modal_results: Sequence[HitModalResult],
    title: str = "Modal extraction",
) -> ModalReportArtifacts:
    ensure_dir(out_dir)

    if len(windows) != len(modal_results):
        raise ValueError(
            f"windows/results length mismatch: {len(windows)} != {len(modal_results)}"
        )

    mdd = MarkdownDoc()
    mdd.h1(title)

    mdd.h2("Hit-by-hit results")
    mdd.p("Per-hit extracted values (one row per detected impact).")

    rows: list[list[str]] = []
    for w, r in zip(windows, modal_results):
        rows.append(
            [
                f"H{r.hit_id:03d}",
                f"{w.t_hit:.3f}",
                f"{r.fn_hz:.2f}" if np.isfinite(r.fn_hz) else "nan",
                f"{r.zeta:.5f}" if np.isfinite(r.zeta) else "nan",
                f"{r.snr_db:.1f}" if np.isfinite(r.snr_db) else "nan",
                f"{r.env_fit_r2:.3f}" if np.isfinite(r.env_fit_r2) else "nan",
                r.reject_reason or "",
            ]
        )

    mdd.table(
        headers=["hit_id", "t_hit (s)", "f_n (Hz)", "zeta", "SNR (dB)", "env R²", "reject"],
        rows=rows,
    )

    # Summary (accepted hits only)
    mdd.h2("Summary")
    ok = [r for r in modal_results if r.reject_reason is None and np.isfinite(r.fn_hz) and np.isfinite(r.zeta)]
    mdd.p(f"Detected hits: **{hit_report.n_hits_used}**. Accepted for summary: **{len(ok)}**.")

    if ok:
        fns = np.array([r.fn_hz for r in ok], dtype=float)
        zts = np.array([r.zeta for r in ok], dtype=float)

        def _iqr(x: np.ndarray) -> float:
            q25, q75 = np.percentile(x, [25.0, 75.0])
            return float(q75 - q25)

        mdd.table(
            headers=["metric", "median", "IQR"],
            rows=[
                ["f_n (Hz)", f"{float(np.median(fns)):.2f}", f"{_iqr(fns):.2f}"],
                ["zeta", f"{float(np.median(zts)):.5f}", f"{_iqr(zts):.5f}"],
            ],
        )
    else:
        mdd.p("No accepted hits (all were rejected). Consider adjusting band limits, settle/ring durations, or QC thresholds.")

    
    mdd.h2("Per-hit deep dive")

    fig_dir = out_dir / "figures" / "modal_hits"
    fig_dir.mkdir(parents=True, exist_ok=True)

    for w, r in zip(windows, modal_results):
        mdd.h3(f"Hit {r.hit_id}")

        # Isolate ringdown segment inside this window using absolute times
        # result.t0_s / t1_s are absolute time in file
        # w.t_start is absolute time of window start
        i0 = int(round((r.t0_s - w.t_start) * stereo.fs))
        i1 = int(round((r.t1_s - w.t_start) * stereo.fs))
        i0 = max(0, min(i0, len(w.accel)))
        i1 = max(i0 + 1, min(i1, len(w.accel)))

        x = np.asarray(w.accel[i0:i1], dtype=float)
        t_abs = w.t_start + (np.arange(len(x), dtype=float) + i0) / stereo.fs

        # Figures
        png_time = fig_dir / f"hit_{r.hit_id:03d}_time.png"
        png_psd = fig_dir / f"hit_{r.hit_id:03d}_psd.png"

        plot_hit_response_with_damping(t_abs=t_abs, x=x, result=r, out_png=png_time)
        plot_hit_spectrum(
            x=x,
            fs=stereo.fs,
            result=r,
            out_png=png_psd,
            fmin_hz=0.0,
            fmax_hz=min(stereo.fs / 2.0, 5000.0),  # or your configured expected range
        )

        # Quick metrics line (keeps it readable)
        mdd.p(
            f"- t_hit={w.t_hit:.3f}s  "
            f"- fn={r.fn_hz:.2f}Hz  "
            f"- zeta={r.zeta:.5f}  "
            f"- SNR={r.snr_db:.1f}dB  "
            f"- R²={r.env_fit_r2:.3f}  "
            f"- reject={(r.reject_reason or 'OK')}"
        )

        # Embed images (paths relative to report file)
        rel_time = png_time.relative_to(out_dir)
        rel_psd = png_psd.relative_to(out_dir)
        mdd.image(str(rel_time), alt=f"Hit {r.hit_id} time response")
        mdd.image(str(rel_psd), alt=f"Hit {r.hit_id} spectrum")
        report_md = out_dir / "report_modal.md"
        report_md.write_text(mdd.to_markdown(), encoding="utf-8")
        return ModalReportArtifacts(report_md=report_md)

