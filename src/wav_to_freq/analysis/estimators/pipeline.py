from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from wav_to_freq.analysis.diagnostics.beating import compute_beating_score
from wav_to_freq.analysis.diagnostics.filter_risk import compute_filter_risk
from wav_to_freq.analysis.diagnostics.inst_freq import compute_inst_freq_jitter
from wav_to_freq.analysis.diagnostics.monotonicity import compute_envelope_increase_frac
from wav_to_freq.analysis.estimators.energy_decay import estimate_energy_decay
from wav_to_freq.analysis.estimators.fd_half_power import estimate_fd_half_power
from wav_to_freq.analysis.estimators.td_envelope import estimate_td_envelope
from wav_to_freq.analysis.status.mapping import assess_estimate
from wav_to_freq.analysis.peaks.config import PsdConfig
from wav_to_freq.dsp.psd import compute_welch_psd
from wav_to_freq.domain.reason_codes import ReasonCode
from wav_to_freq.domain.results import EstimateResult
from wav_to_freq.domain.status import EstimateStatus


def estimate_peak_methods(
    y: np.ndarray,
    *,
    fs: float,
    peak_hz: float,
    psd_cfg: PsdConfig,
    coupled: bool = False,
    peak_detection_count: int | None = None,
    total_hits: int | None = None,
    min_detection_hits: int | None = 2,
    transient_s: float = 0.20,
    established_min_s: float = 0.40,
    established_r2_min: float = 0.95,
    fit_max_s: float = 0.80,
    noise_tail_s: float = 0.20,
    noise_mult: float = 3.0,
    decay_min_duration_s: float = 1.0,
    decay_min_cycles: float = 8.0,
    beating_score_max: float = 0.20,
    envelope_increase_frac_max: float = 0.10,
    inst_freq_rel_jitter_max: float = 0.05,
    filter_q_factor_max: float = 5.0,
) -> list[EstimateResult]:
    """Compute all estimator outputs for a single peak."""

    y_filt = np.asarray(y, dtype=np.float64)
    fs = float(fs)
    peak_hz = float(peak_hz)

    reason_flags: list[ReasonCode] = []
    diagnostics_common: dict[str, float | None] = {}

    beating_score, beating_flag = compute_beating_score(
        y_filt,
        fs,
        fi_hz=peak_hz,
        transient_s=transient_s,
        beating_score_max=beating_score_max,
    )
    diagnostics_common["beating_score"] = beating_score
    if beating_flag:
        reason_flags.append(beating_flag)

    inc_frac, monotonic_flag = compute_envelope_increase_frac(
        y_filt,
        fs,
        fi_hz=peak_hz,
        transient_s=transient_s,
        envelope_increase_frac_max=envelope_increase_frac_max,
    )
    diagnostics_common["envelope_increase_frac"] = inc_frac
    if monotonic_flag:
        reason_flags.append(monotonic_flag)

    _, _, jitter, inst_flag = compute_inst_freq_jitter(
        y_filt,
        fs,
        transient_s=transient_s,
        inst_freq_rel_jitter_max=inst_freq_rel_jitter_max,
    )
    diagnostics_common["inst_freq_rel_jitter"] = jitter
    if inst_flag:
        reason_flags.append(inst_flag)

    lo = max(0.5, 0.6 * peak_hz)
    hi = min(0.49 * fs, 1.4 * peak_hz)
    q_factor, filter_flag = compute_filter_risk(
        fi_hz=peak_hz,
        lo_hz=lo,
        hi_hz=hi,
        q_factor_max=filter_q_factor_max,
    )
    diagnostics_common["filter_q_factor"] = q_factor
    if filter_flag:
        reason_flags.append(filter_flag)

    full_fit, established_fit = estimate_td_envelope(
        y_filt,
        fs,
        fn_hz=peak_hz,
        transient_s=transient_s,
        established_min_s=established_min_s,
        established_r2_min=established_r2_min,
        fit_max_s=fit_max_s,
        noise_tail_s=noise_tail_s,
        noise_mult=noise_mult,
        decay_min_duration_s=decay_min_duration_s,
        decay_min_cycles=decay_min_cycles,
    )

    estimates: list[EstimateResult] = []
    estimates.extend(
        _build_td_estimates(
            full_fit,
            established_fit,
            reason_flags,
            diagnostics_common,
            peak_hz,
        )
    )

    f, pxx = compute_welch_psd(y_filt, fs=fs, cfg=psd_cfg)
    fd = estimate_fd_half_power(
        f,
        pxx,
        peak_hz=peak_hz,
        coupled=coupled,
        peak_detection_count=peak_detection_count,
        total_hits=total_hits,
        min_detection_hits=min_detection_hits,
    )
    diagnostics_fd = {
        "f1_hz": fd.f1_hz,
        "f2_hz": fd.f2_hz,
        "fd_peak_power": fd.peak_power,
        **diagnostics_common,
    }
    estimates.append(
        assess_estimate(
            EstimateResult(
                hit_id=0,
                peak_rank=0,
                method="FD_HALF_POWER",
                fi_bin_hz=peak_hz,
                fi_refined_hz=None,
                zeta=fd.zeta if np.isfinite(fd.zeta) else None,
                status=EstimateStatus.NOT_COMPUTED,
                reason_codes=tuple(list(reason_flags) + list(fd.reason_codes)),
                diagnostics=diagnostics_fd,
            )
        )
    )

    energy = estimate_energy_decay(
        y_filt,
        fs,
        fn_hz=peak_hz,
        transient_s=transient_s,
        fit_max_s=fit_max_s,
        noise_tail_s=noise_tail_s,
        noise_mult=noise_mult,
        decay_min_duration_s=decay_min_duration_s,
        decay_min_cycles=decay_min_cycles,
    )
    diagnostics_energy = {
        "energy_fit_r2": energy.r2,
        "energy_fit_duration_s": energy.duration_s,
        "energy_fit_cycles": energy.n_cycles,
        **diagnostics_common,
    }
    estimates.append(
        assess_estimate(
            EstimateResult(
                hit_id=0,
                peak_rank=0,
                method="ENERGY_ENVELOPE_SQ",
                fi_bin_hz=peak_hz,
                fi_refined_hz=None,
                zeta=energy.zeta if np.isfinite(energy.zeta) else None,
                status=EstimateStatus.NOT_COMPUTED,
                reason_codes=tuple(list(reason_flags) + list(energy.reason_codes)),
                diagnostics=diagnostics_energy,
            )
        )
    )

    return estimates


def _build_td_estimates(
    full_fit,
    established_fit,
    reason_flags: Sequence[ReasonCode],
    diagnostics_common: dict[str, float | None],
    peak_hz: float,
) -> list[EstimateResult]:
    out: list[EstimateResult] = []
    for fit in (full_fit, established_fit):
        diagnostics = {
            "env_fit_r2": fit.r2,
            "env_fit_duration_s": fit.duration_s,
            "env_fit_cycles": fit.n_cycles,
            **diagnostics_common,
        }
        method = "TD_ENVELOPE_FULL" if fit.fit_label == "full" else "TD_ENVELOPE_EST"
        out.append(
            assess_estimate(
                EstimateResult(
                    hit_id=0,
                    peak_rank=0,
                    method=method,
                    fi_bin_hz=peak_hz,
                    fi_refined_hz=None,
                    zeta=fit.zeta if np.isfinite(fit.zeta) else None,
                    status=EstimateStatus.NOT_COMPUTED,
                    reason_codes=tuple(list(reason_flags) + list(fit.reason_codes)),
                    diagnostics=diagnostics,
                )
            )
        )
    return out
