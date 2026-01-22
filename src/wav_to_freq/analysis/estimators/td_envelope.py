from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.signal import hilbert

from wav_to_freq.domain.reason_codes import ReasonCode


@dataclass(frozen=True)
class EnvelopeFitResult:
    fit_label: str
    zeta: float
    r2: float
    log_c: float
    log_m: float
    i0: int
    i1: int
    duration_s: float
    n_cycles: float
    reason_codes: tuple[ReasonCode, ...] = ()


def estimate_td_envelope(
    y: NDArray[np.float64],
    fs: float,
    *,
    fn_hz: float,
    transient_s: float,
    established_min_s: float,
    established_r2_min: float,
    fit_max_s: float,
    noise_tail_s: float,
    noise_mult: float,
    decay_min_duration_s: float,
    decay_min_cycles: float,
) -> tuple[EnvelopeFitResult, EnvelopeFitResult]:
    fs = float(fs)
    fn_hz = float(fn_hz)
    y = np.asarray(y, dtype=np.float64)

    n = y.size
    if n < int(0.2 * fs):
        empty = EnvelopeFitResult(
            fit_label="full",
            zeta=float("nan"),
            r2=float("nan"),
            log_c=float("nan"),
            log_m=float("nan"),
            i0=0,
            i1=n,
            duration_s=0.0,
            n_cycles=0.0,
            reason_codes=(ReasonCode.TOO_SHORT_DECAY,),
        )
        return empty, EnvelopeFitResult(
            fit_label="established",
            zeta=float("nan"),
            r2=float("nan"),
            log_c=float("nan"),
            log_m=float("nan"),
            i0=0,
            i1=n,
            duration_s=0.0,
            n_cycles=0.0,
            reason_codes=(ReasonCode.TOO_SHORT_DECAY,),
        )

    e = _env(y)

    i0_floor = int(round(max(0.0, float(transient_s)) * fs))
    i0_min = int(round(max(float(transient_s), float(established_min_s)) * fs))

    i0_floor = max(0, min(i0_floor, n - 32))
    i0_min = max(i0_floor, min(i0_min, n - 32))

    full = _fit_envelope_segment(
        e,
        fs,
        fn_hz=fn_hz,
        i0=i0_floor,
        fit_label="full",
        fit_max_s=fit_max_s,
        noise_tail_s=noise_tail_s,
        noise_mult=noise_mult,
        decay_min_duration_s=decay_min_duration_s,
        decay_min_cycles=decay_min_cycles,
    )

    step = max(1, int(round(0.005 * fs)))
    best: EnvelopeFitResult | None = None

    for i0 in range(i0_floor, i0_min + 1, step):
        candidate = _fit_envelope_segment(
            e,
            fs,
            fn_hz=fn_hz,
            i0=i0,
            fit_label="established",
            fit_max_s=fit_max_s,
            noise_tail_s=noise_tail_s,
            noise_mult=noise_mult,
            decay_min_duration_s=decay_min_duration_s,
            decay_min_cycles=decay_min_cycles,
        )
        if not np.isfinite(candidate.r2):
            continue
        if candidate.r2 >= established_r2_min:
            best = candidate
            break

    if best is None:
        best = _fit_envelope_segment(
            e,
            fs,
            fn_hz=fn_hz,
            i0=i0_min,
            fit_label="established",
            fit_max_s=fit_max_s,
            noise_tail_s=noise_tail_s,
            noise_mult=noise_mult,
            decay_min_duration_s=decay_min_duration_s,
            decay_min_cycles=decay_min_cycles,
        )

    return full, best


def _fit_envelope_segment(
    e: NDArray[np.float64],
    fs: float,
    *,
    fn_hz: float,
    i0: int,
    fit_label: str,
    fit_max_s: float,
    noise_tail_s: float,
    noise_mult: float,
    decay_min_duration_s: float,
    decay_min_cycles: float,
) -> EnvelopeFitResult:
    fs = float(fs)
    n = int(e.size)
    i1 = _choose_fit_end(
        e,
        fs,
        i0=i0,
        fit_max_s=fit_max_s,
        noise_tail_s=noise_tail_s,
        noise_mult=noise_mult,
    )
    if i1 - i0 < 32:
        return EnvelopeFitResult(
            fit_label=fit_label,
            zeta=float("nan"),
            r2=float("nan"),
            log_c=float("nan"),
            log_m=float("nan"),
            i0=i0,
            i1=i1,
            duration_s=max(0.0, (i1 - i0) / fs),
            n_cycles=0.0,
            reason_codes=(ReasonCode.TOO_SHORT_DECAY,),
        )

    duration_s = (i1 - i0) / fs
    n_cycles = duration_s * float(fn_hz)
    if duration_s < float(decay_min_duration_s) or n_cycles < float(decay_min_cycles):
        return EnvelopeFitResult(
            fit_label=fit_label,
            zeta=float("nan"),
            r2=float("nan"),
            log_c=float("nan"),
            log_m=float("nan"),
            i0=i0,
            i1=i1,
            duration_s=float(duration_s),
            n_cycles=float(n_cycles),
            reason_codes=(ReasonCode.TOO_SHORT_DECAY,),
        )

    t = (np.arange(i0, i1, dtype=np.float64) - float(i0)) / fs
    log_c, log_m, r2 = _fit_log_envelope(t, e[i0:i1])
    alpha = -float(log_m)
    omega_n = 2.0 * np.pi * float(fn_hz)
    zeta = alpha / (omega_n + np.finfo(float).eps)

    return EnvelopeFitResult(
        fit_label=fit_label,
        zeta=float(zeta),
        r2=float(r2),
        log_c=float(log_c),
        log_m=float(log_m),
        i0=i0,
        i1=i1,
        duration_s=float(duration_s),
        n_cycles=float(n_cycles),
        reason_codes=(),
    )


def _env(x: NDArray[np.float64]) -> NDArray[np.float64]:
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return x
    return np.abs(hilbert(x)).astype(np.float64)


def _fit_log_envelope(
    t: NDArray[np.float64], e: NDArray[np.float64]
) -> tuple[float, float, float]:
    t = np.asarray(t, dtype=np.float64)
    e = np.asarray(e, dtype=np.float64)

    if t.size < 8:
        return float("nan"), float("nan"), float("nan")

    eps = np.finfo(float).eps
    ln = np.log(np.clip(e, eps, None))

    log_m, log_c = np.polyfit(t, ln, 1)
    ln_hat = log_c + log_m * t

    ss_res = float(np.sum((ln - ln_hat) ** 2))
    ss_tot = float(np.sum((ln - float(np.mean(ln))) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return float(log_c), float(log_m), float(r2)


def _choose_fit_end(
    e: NDArray[np.float64],
    fs: float,
    *,
    i0: int,
    fit_max_s: float,
    noise_tail_s: float,
    noise_mult: float,
) -> int:
    fs = float(fs)
    n = int(e.size)
    if n <= i0 + 16:
        return n

    i1_cap = min(n, i0 + int(round(max(0.05, float(fit_max_s)) * fs)))

    tail = int(round(max(0.05, float(noise_tail_s)) * fs))
    tail = min(tail, n)
    noise_level = float(np.median(e[n - tail :])) if tail >= 8 else float(np.median(e))
    thresh = float(noise_mult) * max(noise_level, np.finfo(float).eps)

    seg = e[i0:i1_cap]
    below = np.where(seg <= thresh)[0]
    if below.size > 0:
        i1 = i0 + int(below[0])
        return max(i0 + 16, i1)

    return i1_cap
