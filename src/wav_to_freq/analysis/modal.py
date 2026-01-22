# ==== FILE: src/wav_to_freq/modal.py ====

from __future__ import annotations
from typing import Sequence, Optional, cast

import numpy as np
from numpy.typing import NDArray
from scipy.signal import welch, butter, filtfilt

from wav_to_freq.analysis.estimators.td_envelope import estimate_td_envelope
from wav_to_freq.domain.reason_codes import ReasonCode
from wav_to_freq.domain.types import HitModalResult, HitWindow


def analyze_all_hits(
    windows: Sequence[HitWindow],
    fs: float,
    *,
    settle_s: float = 0.010,
    ring_s: float = 1.0,
    fmin_hz: float = 0.5,
    fmax_hz: float = 50.0,
    transient_s: float = 0.20,
    established_min_s: float = 0.40,
    established_r2_min: float = 0.95,
    # NEW: limit fit tail so noise floor doesn't destroy R²
    fit_max_s: float = 0.80,
    noise_tail_s: float = 0.20,
    noise_mult: float = 3.0,
    decay_min_duration_s: float = 1.0,
    decay_min_cycles: float = 8.0,
) -> list[HitModalResult]:
    return [
        analyze_hit(
            w,
            fs,
            settle_s=settle_s,
            ring_s=ring_s,
            fmin_hz=fmin_hz,
            fmax_hz=fmax_hz,
            transient_s=transient_s,
            established_min_s=established_min_s,
            established_r2_min=established_r2_min,
            fit_max_s=fit_max_s,
            noise_tail_s=noise_tail_s,
            noise_mult=noise_mult,
            decay_min_duration_s=decay_min_duration_s,
            decay_min_cycles=decay_min_cycles,
        )
        for w in windows
    ]


def analyze_hit(
    w: HitWindow,
    fs: float,
    *,
    settle_s: float,
    ring_s: float,
    fmin_hz: float,
    fmax_hz: float,
    transient_s: float,
    established_min_s: float,
    established_r2_min: float,
    fit_max_s: float,
    noise_tail_s: float,
    noise_mult: float,
    decay_min_duration_s: float,
    decay_min_cycles: float,
) -> HitModalResult:
    fs = float(fs)
    accel: NDArray[np.float64] = np.asarray(w.accel, dtype=np.float64)

    start = int(round(settle_s * fs))
    end = min(len(accel), start + int(round(ring_s * fs)))

    if end - start < int(0.1 * fs):
        return HitModalResult(
            hit_id=w.hit_id,
            hit_index=w.hit_index,
            t0_s=w.t_start + start / fs,
            t1_s=w.t_start + end / fs,
            fn_hz=float("nan"),
            zeta=float("nan"),
            snr_db=float("nan"),
            env_fit_r2=0.0,
            env_log_c=float("nan"),
            env_log_m=float("nan"),
            reject_reason="ringdown_too_short",
            fit_t0_s=None,
            fit_t1_s=None,
        )

    x = accel[start:end].copy()
    x -= float(np.mean(x))

    # quick SNR-ish metric
    n = len(x)
    a = x[: max(1, n // 5)]
    b = x[max(1, 4 * n // 5) :]
    snr_db = 20.0 * np.log10((float(np.std(a)) + 1e-12) / (float(np.std(b)) + 1e-12))

    fn_hz = _estimate_fn_psd(x, fs, fmin_hz=fmin_hz, fmax_hz=fmax_hz)
    if not np.isfinite(fn_hz) or fn_hz <= 0:
        return HitModalResult(
            hit_id=w.hit_id,
            hit_index=w.hit_index,
            t0_s=w.t_start + start / fs,
            t1_s=w.t_start + end / fs,
            fn_hz=float("nan"),
            zeta=float("nan"),
            snr_db=snr_db,
            env_fit_r2=0.0,
            env_log_c=float("nan"),
            env_log_m=float("nan"),
            reject_reason="no_peak_found",
            fit_t0_s=None,
            fit_t1_s=None,
        )

    y = _bandpass(x, fs, float(fn_hz))

    full_fit, established_fit = estimate_td_envelope(
        y,
        fs,
        fn_hz=float(fn_hz),
        transient_s=transient_s,
        established_min_s=established_min_s,
        established_r2_min=established_r2_min,
        fit_max_s=fit_max_s,
        noise_tail_s=noise_tail_s,
        noise_mult=noise_mult,
        decay_min_duration_s=decay_min_duration_s,
        decay_min_cycles=decay_min_cycles,
    )

    chosen = established_fit
    if (
        not np.isfinite(chosen.zeta)
        or ReasonCode.TOO_SHORT_DECAY in chosen.reason_codes
        or not np.isfinite(chosen.r2)
        or chosen.r2 < established_r2_min
    ):
        chosen = full_fit

    fit_t0_s = w.t_start + (start + chosen.i0) / fs
    fit_t1_s = w.t_start + (start + chosen.i1) / fs

    reject_reason: Optional[str] = None
    if ReasonCode.TOO_SHORT_DECAY in chosen.reason_codes:
        reject_reason = "too_short_decay"
    elif not np.isfinite(chosen.zeta) or chosen.zeta <= 0:
        reject_reason = "bad_zeta"
    elif not np.isfinite(chosen.r2) or chosen.r2 < established_r2_min:
        reject_reason = "low_r2"

    return HitModalResult(
        hit_id=w.hit_id,
        hit_index=w.hit_index,
        t0_s=w.t_start + start / fs,
        t1_s=w.t_start + end / fs,
        fn_hz=float(fn_hz),
        zeta=float(chosen.zeta),
        snr_db=float(snr_db),
        env_fit_r2=float(chosen.r2),
        env_log_c=float(chosen.log_c),
        env_log_m=float(chosen.log_m),
        reject_reason=reject_reason,
        fit_t0_s=float(fit_t0_s) if np.isfinite(fit_t0_s) else None,
        fit_t1_s=float(fit_t1_s) if np.isfinite(fit_t1_s) else None,
    )


def _estimate_fn_psd(
    x: NDArray[np.float64], fs: float, *, fmin_hz: float, fmax_hz: float
) -> float:
    fs = float(fs)
    x = np.asarray(x, dtype=np.float64)
    if x.size < 16:
        return float("nan")

    result = welch(x, fs=fs, nperseg=min(4096, max(256, x.size // 2)))
    if result is None:
        return float("nan")
    f = np.asarray(result[0], dtype=np.float64)
    pxx = np.asarray(result[1], dtype=np.float64)
    m = (f >= float(fmin_hz)) & (f <= float(fmax_hz))
    if not np.any(m):
        return float("nan")

    ff = f[m]
    pp = pxx[m]
    if pp.size == 0:
        return float("nan")

    k = int(np.argmax(pp))
    return float(ff[k])


def _bandpass(x: NDArray[np.float64], fs: float, fn_hz: float) -> NDArray[np.float64]:
    fs = float(fs)
    fn_hz = float(fn_hz)

    lo = max(0.5, 0.6 * fn_hz)
    hi = min(0.49 * fs, 1.4 * fn_hz)
    if hi <= lo:
        return np.asarray(x, dtype=np.float64)

    result = cast(
        tuple[NDArray[np.float64], NDArray[np.float64]],
        butter(
            4,
            [lo / (0.5 * fs), hi / (0.5 * fs)],
            btype="bandpass",
            output="ba",
        ),
    )
    b = np.asarray(result[0], dtype=np.float64)
    a = np.asarray(result[1], dtype=np.float64)
    return filtfilt(b, a, x).astype(np.float64)
