from pathlib import Path
from typing import Sequence
from wav_to_freq.domain.results import EstimateResult
from wav_to_freq.domain.types import HitModalResult, HitWindow
from wav_to_freq.reporting.doc import ReportDoc
from wav_to_freq.reporting.plots import plot_hit_response_report
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

    headers = ["mode"]
    header_groups: list[tuple[str, int]] = [("", 1)]
    for hit_id in hit_ids:
        label = f"H{hit_id:03d}"
        header_groups.append((label, 4))
        headers.extend(["f_i", "zeta_TD", "zeta_FD", "zeta_E"])

    rows: list[list[str]] = []
    for rank in range(1, max_summary_peaks + 1):
        row = [str(rank)]
        for hit_id in hit_ids:
            hit_estimates = [
                e
                for e in estimates
                if int(e.hit_id) == hit_id and int(e.peak_rank) == rank
            ]
            fi = _pick_fi(hit_estimates)
            zeta_td = _pick_zeta(hit_estimates, ("TD_ENVELOPE_EST", "TD_ENVELOPE_FULL"))
            zeta_fd = _pick_zeta(hit_estimates, ("FD_HALF_POWER",))
            zeta_energy = _pick_zeta(hit_estimates, ("ENERGY_ENVELOPE_SQ",))
            row.extend(
                [
                    _format_fi(fi),
                    _format_zeta_percent(zeta_td),
                    _format_zeta_percent(zeta_fd),
                    _format_zeta_percent(zeta_energy),
                ]
            )
        rows.append(row)

    mdd.h2("Hit Summary (fi, zeta)")
    mdd.table(headers, rows, header_groups=header_groups)


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
    transient_s: float,
    fs: float,
    hits_dir: Path,
    out_dir: Path,
):
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
                f"fn={custom_format(float(r.fn_hz), '.3f')} Hz",
                f"zeta={custom_format(float(r.zeta), '.6f')}",
                f"SNR={custom_format(float(r.snr_db), '.2f')} dB",
                f"R²={custom_format(float(r.env_fit_r2), '.3f')}",
            ]
            + ([f"reject_reason: `{r.reject_reason}`"] if r.reject_reason else [])
            + (
                ["flags: " + ", ".join(f"`{c.value}`" for c in r.reason_codes)]
                if r.reason_codes
                else []
            )
        )
        mdd.image(out_png.relative_to(out_dir).as_posix(), alt=f"{label} response")
