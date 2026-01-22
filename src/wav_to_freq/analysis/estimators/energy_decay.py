from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
from numpy.typing import NDArray
from scipy.signal import hilbert

from wav_to_freq.domain.reason_codes import ReasonCode


@dataclass(frozen=True)
class EnergyDecayResult:
    zeta: float
    log_c: float
    log_m: float
    r2: float
    i0: int
    i1: int
    duration_s: float
    n_cycles: float
    reason_codes: tuple[ReasonCode, ...] = ()


def estimate_energy_decay(
    y_filt: NDArray[np.float64],
    fs: float,
    *,
    fn_hz: float,
    transient_s: float,
    fit_max_s: float,
    noise_tail_s: float,
    noise_mult: float,
    decay_min_duration_s: float,
    decay_min_cycles: float,
) -> EnergyDecayResult:
    fs = float(fs)
    fn_hz = float(fn_hz)
    y = np.asarray(y_filt, dtype=np.float64)
    if y.size < int(0.2 * fs):
        return _not_computed(0, y.size, ReasonCode.TOO_SHORT_DECAY)

    result = hilbert(y)
    if result is None:
        return _not_computed(0, y.size, ReasonCode.TOO_SHORT_DECAY)
    if isinstance(result, tuple):
        result = result[0]
    env = np.abs(np.asarray(result, dtype=np.complex128)).astype(np.float64)
    energy = env**2

    i0 = int(round(max(0.0, float(transient_s)) * fs))
    i0 = max(0, min(i0, energy.size - 32))
    i1 = _choose_fit_end(
        energy,
        fs,
        i0=i0,
        fit_max_s=fit_max_s,
        noise_tail_s=noise_tail_s,
        noise_mult=noise_mult,
    )
    duration_s = (i1 - i0) / fs
    n_cycles = duration_s * fn_hz
    if duration_s < float(decay_min_duration_s) or n_cycles < float(decay_min_cycles):
        return _not_computed(i0, i1, ReasonCode.TOO_SHORT_DECAY)

    t = (np.arange(i0, i1, dtype=np.float64) - float(i0)) / fs
    log_c, log_m, r2 = _fit_log_energy(t, energy[i0:i1])
    alpha = -float(log_m)
    omega_n = 2.0 * np.pi * fn_hz
    zeta = alpha / (4.0 * omega_n + np.finfo(float).eps)
    if not np.isfinite(zeta) or zeta <= 0:
        return _not_computed(i0, i1, ReasonCode.BAD_ZETA_ENERGY)

    return EnergyDecayResult(
        zeta=float(zeta),
        log_c=float(log_c),
        log_m=float(log_m),
        r2=float(r2),
        i0=i0,
        i1=i1,
        duration_s=float(duration_s),
        n_cycles=float(n_cycles),
        reason_codes=(ReasonCode.EFFECTIVE_DAMPING_ONLY,),
    )


def _fit_log_energy(
    t: NDArray[np.float64], energy: NDArray[np.float64]
) -> tuple[float, float, float]:
    t = np.asarray(t, dtype=np.float64)
    energy = np.asarray(energy, dtype=np.float64)
    if t.size < 8:
        return float("nan"), float("nan"), float("nan")

    eps = np.finfo(float).eps
    ln = np.log(np.clip(energy, eps, None))
    log_m, log_c = np.polyfit(t, ln, 1)
    ln_hat = log_c + log_m * t
    ss_res = float(np.sum((ln - ln_hat) ** 2))
    ss_tot = float(np.sum((ln - float(np.mean(ln))) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return float(log_c), float(log_m), float(r2)


def _choose_fit_end(
    energy: NDArray[np.float64],
    fs: float,
    *,
    i0: int,
    fit_max_s: float,
    noise_tail_s: float,
    noise_mult: float,
) -> int:
    fs = float(fs)
    n = int(energy.size)
    if n <= i0 + 16:
        return n

    i1_cap = min(n, i0 + int(round(max(0.05, float(fit_max_s)) * fs)))
    tail = int(round(max(0.05, float(noise_tail_s)) * fs))
    tail = min(tail, n)
    noise_level = (
        float(np.median(energy[n - tail :])) if tail >= 8 else float(np.median(energy))
    )
    thresh = float(noise_mult) * max(noise_level, np.finfo(float).eps)

    seg = energy[i0:i1_cap]
    below = np.where(seg <= thresh)[0]
    if below.size > 0:
        i1 = i0 + int(below[0])
        return max(i0 + 16, i1)

    return i1_cap


def _not_computed(i0: int, i1: int, reason: ReasonCode) -> EnergyDecayResult:
    return EnergyDecayResult(
        zeta=float("nan"),
        log_c=float("nan"),
        log_m=float("nan"),
        r2=float("nan"),
        i0=int(i0),
        i1=int(i1),
        duration_s=0.0,
        n_cycles=0.0,
        reason_codes=(reason, ReasonCode.EFFECTIVE_DAMPING_ONLY),
    )
