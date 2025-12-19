# ==== FILE: src/wav_to_freq/modal.py ====

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

    # New: absolute time range actually used for the decay fit
    fit_t0_s: float
    fit_t1_s: float

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

    # Absolute times of the ringdown segment inside the WAV file
    t0_abs = w.t_start + start / fs
    t1_abs = w.t_start + end / fs

    if end - start < int(0.1 * fs):
        return HitModalResult(
            hit_id=w.hit_id,
            hit_index=w.hit_index,
            t0_s=t0_abs,
            t1_s=t1_abs,
            fn_hz=float("nan"),
            zeta=float("nan"),
            snr_db=float("nan"),
            env_fit_r2=0.0,
            env_log_c=float("nan"),
            env_log_m=float("nan"),
            fit_t0_s=float("nan"),
            fit_t1_s=float("nan"),
            reject_reason="ringdown_too_short",
        )

    x = accel[start:end].copy()
    x -= np.mean(x)

    # crude SNR proxy: compare early chunk vs late chunk
    n = len(x)
    a = x[: max(1, n // 5)]
    b = x[max(1, 4 * n // 5) :]
    snr_db = 20.0 * np.log10((np.std(a) + 1e-12) / (np.std(b) + 1e-12))

    fn_hz = _estimate_fn_psd(x, fs, fmin_hz=fmin_hz, fmax_hz=fmax_hz)
    if not np.isfinite(fn_hz) or fn_hz <= 0:
        return HitModalResult(
            hit_id=w.hit_id,
            hit_index=w.hit_index,
            t0_s=t0_abs,
            t1_s=t1_abs,
            fn_hz=float("nan"),
            zeta=float("nan"),
            snr_db=float(snr_db),
            env_fit_r2=0.0,
            env_log_c=float("nan"),
            env_log_m=float("nan"),
            fit_t0_s=float("nan"),
            fit_t1_s=float("nan"),
            reject_reason="no_peak_found",
        )

    x_bp = _bandpass(x, fs, low_hz=max(0.05, 0.7 * fn_hz), high_hz=1.3 * fn_hz)

    # NOTE: now returns fit window indices too
    zeta, r2, c, m, i0_fit, i1_fit = _estimate_zeta_envelope_auto(x_bp, fs, fn_hz)

    # Map fit indices to absolute time in the file
    # t_rel = np.arange(n)/fs for the ringdown segment
    fit_t0_s = t0_abs + (i0_fit / fs if np.isfinite(i0_fit) else float("nan"))
    fit_t1_s = t0_abs + (i1_fit / fs if np.isfinite(i1_fit) else float("nan"))

    reject = None
    if not np.isfinite(zeta) or zeta <= 0 or zeta > 0.5:
        reject = "bad_zeta"
    if r2 < 0.6:
        reject = (reject + "|low_r2") if reject else "low_r2"

    return HitModalResult(
        hit_id=w.hit_id,
        hit_index=w.hit_index,
        t0_s=t0_abs,
        t1_s=t1_abs,
        fn_hz=float(fn_hz),
        zeta=float(zeta),
        snr_db=float(snr_db),
        env_fit_r2=float(r2),
        env_log_c=float(c),
        env_log_m=float(m),
        fit_t0_s=float(fit_t0_s),
        fit_t1_s=float(fit_t1_s),
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


def _linreg_r2(tt: NDArray[np.float64], yy: NDArray[np.float64]) -> tuple[float, float, float]:
    """
    Fit yy ~= c + m*tt and return (c, m, r2).
    """
    A = np.vstack([np.ones_like(tt), tt]).T
    coef, *_ = np.linalg.lstsq(A, yy, rcond=None)
    c, m = float(coef[0]), float(coef[1])

    yhat = c + m * tt
    ss_res = float(np.sum((yy - yhat) ** 2))
    ss_tot = float(np.sum((yy - np.mean(yy)) ** 2)) + 1e-12
    r2 = 1.0 - ss_res / ss_tot
    return c, m, r2


def _estimate_zeta_envelope_auto(
    x_bp: NDArray[np.float64],
    fs: float,
    fn_hz: float,
) -> tuple[float, float, float, float, int, int]:
    """
    Automatic selection of an 'established decay' region:
      - compute envelope via Hilbert
      - work in log-domain: y = log(env)
      - search for a start index i0 that maximizes R² of a linear fit on [i0:i1]
        where i1 is near the tail (default 85% of the segment).
    Returns:
      (zeta, r2, c, m, i0_fit, i1_fit)
    """
    env = np.abs(hilbert(x_bp)) + 1e-12
    t = np.arange(len(env), dtype=np.float64) / fs
    y = np.log(env)

    n = len(y)
    if n < 30:
        return float("nan"), 0.0, float("nan"), float("nan"), 0, max(0, n - 1)

    # End of fit: avoid the very end where envelope may hit numerical floor/noise
    i1 = int(max(10, round(0.85 * n)))

    # Candidate start region:
    # - too early -> includes filter transient / multi-mode / nonlinearity
    # - too late -> not enough dynamic range / noisy tail
    i0_min = int(round(0.02 * n))
    i0_max = int(round(0.45 * n))
    i0_max = min(i0_max, i1 - 12)

    if i0_max <= i0_min:
        i0_min = max(0, i1 - 20)
        i0_max = max(i0_min, i1 - 12)

    best = None  # (score, i0, c, m, r2)

    # Step size: about 1% of the record (at least 1 sample)
    step = max(1, int(round(0.01 * n)))

    for i0 in range(i0_min, i0_max + 1, step):
        tt = t[i0:i1]
        yy = y[i0:i1]
        if len(tt) < 12:
            continue

        c, m, r2 = _linreg_r2(tt, yy)

        # We expect decay => slope negative (m < 0)
        if not np.isfinite(m) or m >= 0:
            continue
        if not np.isfinite(r2):
            continue

        # Soft penalty if window is too short (prefer a decent span)
        span_s = float(tt[-1] - tt[0])
        # encourages at least a few cycles; 3/fn is a decent minimum heuristic
        min_span = 3.0 / max(fn_hz, 1e-6)
        penalty = 0.0 if span_s >= min_span else (min_span - span_s) / min_span

        score = float(r2) - 0.15 * penalty

        if best is None or score > best[0]:
            best = (score, i0, c, m, r2)

    if best is None:
        # fallback: original heuristic window
        i0 = max(0, int(0.05 * n))
        tt = t[i0:i1]
        yy = y[i0:i1]
        c, m, r2 = _linreg_r2(tt, yy)
        alpha = -m
        omega_n = 2.0 * np.pi * fn_hz
        zeta = alpha / (omega_n + 1e-12)
        return float(zeta), float(r2), float(c), float(m), int(i0), int(i1)

    _, i0_fit, c_fit, m_fit, r2_fit = best

    alpha = -m_fit
    omega_n = 2.0 * np.pi * fn_hz
    zeta = alpha / (omega_n + 1e-12)

    return float(zeta), float(r2_fit), float(c_fit), float(m_fit), int(i0_fit), int(i1)

