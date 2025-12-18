from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Optional

import numpy as np
from numpy.typing import NDArray

from scipy.signal import welch, butter, filtfilt, hilbert

from wav_to_freq.impact_io import HitWindow


@dataclass(frozen=True)
class HitModalResult:
    hit_id: int
    hit_index: int
    t0_s: float
    t1_s: float
    fn_hz: float
    zeta: float
    snr_db: float
    env_fit_r2: float
    env_log_c: float
    env_log_m: float
    reject_reason: Optional[str] = None


def analyze_all_hits(
    windows: Sequence[HitWindow],
    fs: float,
    *,
    settle_s: float = 0.010,
    ring_s: float = 1.0,
    fmin_hz: float = 0.5,
    fmax_hz: float = 50.0,
) -> list[HitModalResult]:
    return [
        analyze_hit(
            w,
            fs,
            settle_s=settle_s,
            ring_s=ring_s,
            fmin_hz=fmin_hz,
            fmax_hz=fmax_hz,
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
) -> HitModalResult:
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
        )

    x = accel[start:end].copy()
    x -= np.mean(x)

    n = len(x)
    a = x[: max(1, n // 5)]
    b = x[max(1, 4 * n // 5) :]
    snr_db = 20.0 * np.log10((np.std(a) + 1e-12) / (np.std(b) + 1e-12))

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
        )

    x_bp = _bandpass(x, fs, low_hz=max(0.05, 0.7 * fn_hz), high_hz=1.3 * fn_hz)
    zeta, r2, c, m = _estimate_zeta_envelope(x_bp, fs, fn_hz)

    reject = None
    if not np.isfinite(zeta) or zeta <= 0 or zeta > 0.5:
        reject = "bad_zeta"
    if r2 < 0.6:
        reject = (reject + "|low_r2") if reject else "low_r2"

    return HitModalResult(
        hit_id=w.hit_id,
        hit_index=w.hit_index,
        t0_s=w.t_start + start / fs,
        t1_s=w.t_start + end / fs,
        fn_hz=float(fn_hz),
        zeta=float(zeta),
        snr_db=float(snr_db),
        env_fit_r2=float(r2),
        env_log_c=float(c),
        env_log_m=float(m),
        reject_reason=reject,
    )


def _estimate_fn_psd(x: NDArray[np.float64], fs: float, *, fmin_hz: float, fmax_hz: float) -> float:
    nperseg = int(min(len(x), max(256, 2 ** int(np.floor(np.log2(len(x)))))))
    f, pxx = welch(x, fs=fs, nperseg=nperseg)
    mask = (f >= fmin_hz) & (f <= fmax_hz)
    if not np.any(mask):
        return float("nan")
    f2 = f[mask]
    p2 = pxx[mask]
    return float(f2[int(np.argmax(p2))])


def _bandpass(x: NDArray[np.float64], fs: float, *, low_hz: float, high_hz: float) -> NDArray[np.float64]:
    nyq = 0.5 * fs
    low = max(1e-6, low_hz / nyq)
    high = min(0.999999, high_hz / nyq)
    if high <= low:
        return x
    b, a = butter(N=4, Wn=[low, high], btype="bandpass")
    return filtfilt(b, a, x)


def _estimate_zeta_envelope(x_bp: NDArray[np.float64], fs: float, fn_hz: float) -> tuple[float, float, float, float]:
    env = np.abs(hilbert(x_bp)) + 1e-12
    t = np.arange(len(env)) / fs
    y = np.log(env)

    n = len(y)
    i0 = max(0, int(0.05 * n))
    i1 = max(i0 + 10, int(0.85 * n))

    tt = t[i0:i1]
    yy = y[i0:i1]

    A = np.vstack([np.ones_like(tt), tt]).T
    coef, *_ = np.linalg.lstsq(A, yy, rcond=None)
    c, m = float(coef[0]), float(coef[1])

    yhat = c + m * tt
    ss_res = float(np.sum((yy - yhat) ** 2))
    ss_tot = float(np.sum((yy - np.mean(yy)) ** 2)) + 1e-12
    r2 = 1.0 - ss_res / ss_tot

    alpha = -m
    omega_n = 2.0 * np.pi * fn_hz
    zeta = alpha / (omega_n + 1e-12)
    return zeta, r2, c, m

