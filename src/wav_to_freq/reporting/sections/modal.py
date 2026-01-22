from pathlib import Path
from typing import Sequence
from wav_to_freq.domain.types import HitModalResult, HitWindow
from wav_to_freq.reporting.markdown import MarkdownDoc
from wav_to_freq.reporting.plots import plot_hit_response_report
from wav_to_freq.utils.formating import (
    custom_format,
    custom_max,
    custom_mean,
    custom_min,
    is_finite,
)


def add_section_modal_summary(
    mdd: MarkdownDoc, *, results: Sequence[HitModalResult], title: str
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
    mdd: MarkdownDoc,
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
        )
        mdd.image(out_png.relative_to(out_dir).as_posix(), alt=f"{label} response")
