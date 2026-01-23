from pathlib import Path
from typing import Sequence

import numpy as np

from wav_to_freq.analysis import modal
from wav_to_freq.analysis.peaks.config import PsdConfig
from wav_to_freq.domain.results import EstimateResult
from wav_to_freq.domain.types import HitModalResult, HitWindow
from wav_to_freq.dsp.psd import compute_welch_psd
from wav_to_freq.reporting.doc import ReportDoc
from wav_to_freq.reporting.plots import plot_hit_response_report
from wav_to_freq.reporting.plots_diagnostic import (
    plot_energy_decay_diagnostic,
    plot_fd_half_power_diagnostic,
    plot_filtered_response,
    plot_td_envelope_diagnostic,
)
from wav_to_freq.utils.formating import (
    custom_format,
    custom_max,
    custom_mean,
    custom_min,
    is_finite,
)


def _pick_fi(estimates: Sequence[EstimateResult]) -> float | None:
    for estimate in estimates:
        if estimate.fi_bin_hz is not None:
            return float(estimate.fi_bin_hz)
    return None


def _pick_zeta(
    estimates: Sequence[EstimateResult], methods: tuple[str, ...]
) -> float | None:
    for method in methods:
        for estimate in estimates:
            if estimate.method == method and estimate.zeta is not None:
                return float(estimate.zeta)
    return None


def _format_fi(value: float | None) -> str:
    if value is None:
        return ""
    return custom_format(float(value), ".1f")


def _format_zeta_percent(value: float | None) -> str:
    if value is None:
        return ""
    percent = float(value) * 100.0
    return f"{custom_format(percent, '.1f')}%"


def _add_hit_summary_table(
    mdd: ReportDoc,
    *,
    estimates: Sequence[EstimateResult],
    results: Sequence[HitModalResult],
    max_summary_peaks: int,
) -> None:
    hit_ids = sorted({int(r.hit_id) for r in results})
    if not hit_ids or max_summary_peaks <= 0:
        return

    # Table: hits/methods as rows, modes as columns
    headers = ["hit", ""]
    for rank in range(1, max_summary_peaks + 1):
        headers.append(str(rank))

    rows: list[list[str]] = []
    for hit_id in hit_ids:
        label = f"H{hit_id:03d}"
        for method_label, method_names in [
            ("f_i", None),
            ("zeta_TD", ("TD_ENVELOPE_EST", "TD_ENVELOPE_FULL")),
            ("zeta_FD", ("FD_HALF_POWER",)),
            ("zeta_E", ("ENERGY_ENVELOPE_SQ",)),
        ]:
            row = [label if method_label == "f_i" else "", method_label]
            for rank in range(1, max_summary_peaks + 1):
                hit_estimates = [
                    e
                    for e in estimates
                    if int(e.hit_id) == hit_id and int(e.peak_rank) == rank
                ]
                if method_names is None:
                    fi = _pick_fi(hit_estimates)
                    row.append(_format_fi(fi))
                else:
                    zeta = _pick_zeta(hit_estimates, method_names)
                    row.append(_format_zeta_percent(zeta))
            rows.append(row)

    mdd.h2("Hit Summary (fi, zeta)")
    mdd.table(headers, rows)


def add_section_modal_summary(
    mdd: ReportDoc,
    *,
    results: Sequence[HitModalResult],
    estimates: Sequence[EstimateResult] | None = None,
    title: str,
    max_summary_peaks: int = 5,
):
    accepted = [r for r in results if not r.reject_reason]
    rejected = [r for r in results if r.reject_reason]

    fn_vals = [float(r.fn_hz) for r in accepted if is_finite(r.fn_hz)]
    zeta_vals = [float(r.zeta) for r in accepted if is_finite(r.zeta)]
    snr_vals = [float(r.snr_db) for r in accepted if is_finite(r.snr_db)]
    r2_vals = [float(r.env_fit_r2) for r in accepted if is_finite(r.env_fit_r2)]

    mdd.h1(title)

    mdd.bullet(
        [
            f"Total hits: **{len(results)}**",
            f"Accepted: **{len(accepted)}**",
            f"Rejected: **{len(rejected)}**",
        ]
    )

    mdd.p(
        "Note: FD half-power damping estimates (when enabled) are flagged with "
        "`MULTI_MODE_SUSPECTED` when peaks are coupled or appear in only a few hits. "
        "Use the time-domain envelope estimate as the primary reference for lightly "
        "damped structures."
    )

    if estimates:
        _add_hit_summary_table(
            mdd,
            estimates=estimates,
            results=results,
            max_summary_peaks=max_summary_peaks,
        )

    if accepted:
        mdd.h2("Accepted summary")
        items: list[str] = []
        if fn_vals:
            items.append(
                f"fn (Hz): mean={custom_format(custom_mean(fn_vals), '.3f')}, min={custom_format(custom_min(fn_vals), '.3f')}, max={custom_format(custom_max(fn_vals), '.3f')}"
            )
        if zeta_vals:
            items.append(
                f"zeta: mean={custom_format(custom_mean(zeta_vals), '.6f')}, min={custom_format(custom_min(zeta_vals), '.6f')}, max={custom_format(custom_max(zeta_vals), '.6f')}"
            )
        if snr_vals:
            items.append(
                f"SNR (dB): mean={custom_format(custom_mean(snr_vals), '.2f')}, min={custom_format(custom_min(snr_vals), '.2f')}, max={custom_format(custom_max(snr_vals), '.2f')}"
            )
        if r2_vals:
            items.append(
                f"Envelope fit R²: mean={custom_format(custom_mean(r2_vals), '.3f')}, min={custom_format(custom_min(r2_vals), '.3f')}, max={custom_format(custom_max(r2_vals), '.3f')}"
            )
        mdd.bullet(items)

    if rejected:
        mdd.h2("Rejections (by reason)")
        counts: dict[str, int] = {}
        for r in rejected:
            key = r.reject_reason or "unknown"
            counts[key] = counts.get(key, 0) + 1
        mdd.bullet(
            [
                f"{k}: {v}"
                for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
            ]
        )


def add_section_per_hit_results(
    mdd: ReportDoc,
    windows: Sequence[HitWindow],
    results: Sequence[HitModalResult],
    estimates: Sequence[EstimateResult] | None,
    transient_s: float,
    fs: float,
    hits_dir: Path,
    out_dir: Path,
    settle_s: float = 0.010,
    ring_s: float = 1.0,
):
    mdd.h1("Hits")

    if estimates is None:
        estimates = []

    hit_ids = sorted({int(r.hit_id) for r in results})
    for hit_id in hit_ids:
        label = f"H{hit_id:03d}"

        mdd.h2(label)

        # TD and FD plots for the hit (existing logic placeholder)
        out_png = hits_dir / f"{label}_response.png"
        hit_window = next((w for w in windows if int(w.hit_id) == hit_id), None)
        hit_result = next((r for r in results if int(r.hit_id) == hit_id), None)

        if hit_window and hit_result:
            plot_hit_response_report(
                fs=fs,
                window=hit_window,
                result=hit_result,
                out_png=out_png,
                transient_s=transient_s,
            )
            mdd.image(out_png.relative_to(out_dir).as_posix(), alt=f"{label} response")

        # Get all peaks for this hit
        hit_estimates = [e for e in estimates if int(e.hit_id) == hit_id]
        peak_ranks = sorted({int(e.peak_rank) for e in hit_estimates})

        for peak_rank in peak_ranks:
            peak_estimates = [e for e in hit_estimates if int(e.peak_rank) == peak_rank]
            if not peak_estimates:
                continue

            fi_hz = _pick_fi(peak_estimates)
            if fi_hz is None:
                continue

            mdd.h3(f"Peak {peak_rank} - f_{peak_rank} = {_format_fi(fi_hz)} Hz")

            # Plot filtered response for this peak
            if hit_window:
                start = int(round(settle_s * float(fs)))
                end = min(hit_window.accel.size, start + int(round(ring_s * float(fs))))
                segment = np.asarray(hit_window.accel[start:end], dtype=np.float64)
                segment = segment - float(np.mean(segment))
                y_filt = modal._bandpass(segment, float(fs), float(fi_hz))

                filt_png = hits_dir / f"{label}_peak{peak_rank}_filtered.png"
                plot_filtered_response(y_filt, fs=fs, fi_hz=fi_hz, out_png=filt_png)
                mdd.image(
                    filt_png.relative_to(out_dir).as_posix(),
                    alt=f"{label} peak {peak_rank} filtered",
                )
            else:
                y_filt = None

            # Add per-method subsections
            _add_method_section(
                mdd,
                peak_estimates,
                "TD_ENVELOPE_EST",
                "zeta_TD",
                peak_rank,
                label,
                y_filt,
                fs,
                transient_s,
                hits_dir,
                out_dir,
            )
            _add_method_section(
                mdd,
                peak_estimates,
                "FD_HALF_POWER",
                "zeta_FD",
                peak_rank,
                label,
                y_filt,
                fs,
                transient_s,
                hits_dir,
                out_dir,
            )
            _add_method_section(
                mdd,
                peak_estimates,
                "ENERGY_ENVELOPE_SQ",
                "zeta_E",
                peak_rank,
                label,
                y_filt,
                fs,
                transient_s,
                hits_dir,
                out_dir,
            )


def _add_method_section(
    mdd: ReportDoc,
    peak_estimates: Sequence[EstimateResult],
    method: str,
    label: str,
    peak_rank: int,
    hit_label: str,
    y_filt: np.ndarray | None,
    fs: float,
    transient_s: float,
    hits_dir: Path,
    out_dir: Path,
) -> None:
    estimate = next((e for e in peak_estimates if e.method == method), None)
    if estimate is None or estimate.zeta is None:
        mdd.h4(f"{label}_{peak_rank} = NOT_COMPUTED")
        if estimate and estimate.reason_codes:
            mdd.bullet([f"Reason: {', '.join(c.value for c in estimate.reason_codes)}"])
        return

    zeta_percent = estimate.zeta * 100.0
    mdd.h4(f"{label}_{peak_rank} = {custom_format(zeta_percent, '.1f')}%")

    # Show status and reason codes
    info = [f"Status: {estimate.status.value}"]
    if estimate.reason_codes:
        info.append(f"Flags: {', '.join(c.value for c in estimate.reason_codes)}")
    mdd.bullet(info)

    # Show key diagnostics
    if estimate.diagnostics:
        diag_items = []
        for key in [
            "beating_score",
            "envelope_increase_frac",
            "inst_freq_rel_jitter",
            "filter_q_factor",
            "env_fit_r2",
            "energy_fit_r2",
        ]:
            val = estimate.diagnostics.get(key)
            if val is not None:
                try:
                    fval = float(val)
                    if np.isfinite(fval):
                        diag_items.append(f"{key}: {custom_format(fval, '.3f')}")
                except (TypeError, ValueError):
                    pass
        if diag_items:
            mdd.bullet(diag_items)

    # Add diagnostic plots
    if y_filt is None or y_filt.size == 0:
        return

    y = np.asarray(y_filt, dtype=np.float64)

    if method.startswith("TD_ENVELOPE"):
        plot_png = hits_dir / f"{hit_label}_peak{peak_rank}_{method.lower()}_diag.png"
        plot_td_envelope_diagnostic(
            y,
            fs=fs,
            estimate=estimate,
            out_png=plot_png,
            transient_s=transient_s,
        )
        mdd.image(
            plot_png.relative_to(out_dir).as_posix(),
            alt=f"TD diagnostic peak {peak_rank}",
        )

    elif method == "FD_HALF_POWER":
        psd_cfg = PsdConfig(df_target_hz=0.25)
        f, pxx = compute_welch_psd(y, fs=fs, cfg=psd_cfg)
        plot_png = hits_dir / f"{hit_label}_peak{peak_rank}_fd_diag.png"
        plot_fd_half_power_diagnostic(
            f,
            pxx,
            estimate=estimate,
            out_png=plot_png,
        )
        mdd.image(
            plot_png.relative_to(out_dir).as_posix(),
            alt=f"FD diagnostic peak {peak_rank}",
        )

    elif method == "ENERGY_ENVELOPE_SQ":
        plot_png = hits_dir / f"{hit_label}_peak{peak_rank}_energy_diag.png"
        plot_energy_decay_diagnostic(
            y,
            fs=fs,
            estimate=estimate,
            out_png=plot_png,
            transient_s=transient_s,
        )
        mdd.image(
            plot_png.relative_to(out_dir).as_posix(),
            alt=f"Energy diagnostic peak {peak_rank}",
        )
