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
    reject_reason: Optional[str] = None

    # New: fit window chosen by analysis (absolute timestamps)
    fit_t0_s: float | None = None
    fit_t1_s: float | None = None


def analyze_all_hits(
    windows: Sequence[HitWindow],
    fs: float,
    *,
    settle_s: float = 0.010,
    ring_s: float = 1.0,
    fmin_hz: float = 0.5,
    fmax_hz: float = 50.0,
    # established-decay selection (analysis-owned)
    transient_s: float = 0.20,
    established_min_s: float = 0.40,
    established_r2_min: float = 0.95,
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

    # bandpass around fn
    y = _bandpass(x, fs, fn_hz)

    # analysis-owned: choose established decay start, then fit envelope on that region
    zeta, r2, c, m, i0_fit, i1_fit = _estimate_zeta_envelope_auto(
        y,
        fs,
        fn_hz=fn_hz,
        transient_s=transient_s,
        established_min_s=established_min_s,
        established_r2_min=established_r2_min,
    )

    fit_t0_s = w.t_start + (start + i0_fit) / fs
    fit_t1_s = w.t_start + (start + i1_fit) / fs

    reject_reason: Optional[str] = None
    if not np.isfinite(zeta) or zeta <= 0:
        reject_reason = "bad_zeta"
    elif not np.isfinite(r2) or r2 < established_r2_min:
        reject_reason = "low_r2"

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
        reject_reason=reject_reason,
        fit_t0_s=float(fit_t0_s) if np.isfinite(fit_t0_s) else None,
        fit_t1_s=float(fit_t1_s) if np.isfinite(fit_t1_s) else None,
    )


def _estimate_fn_psd(x: NDArray[np.float64], fs: float, *, fmin_hz: float, fmax_hz: float) -> float:
    fs = float(fs)
    x = np.asarray(x, dtype=np.float64)
    if x.size < 16:
        return float("nan")

    f, pxx = welch(x, fs=fs, nperseg=min(4096, max(256, x.size // 2)))
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

    # reasonable band around fn (wide enough to keep the decay shape)
    lo = max(0.5, 0.6 * fn_hz)
    hi = min(0.49 * fs, 1.4 * fn_hz)
    if hi <= lo:
        return np.asarray(x, dtype=np.float64)

    b, a = butter(4, [lo / (0.5 * fs), hi / (0.5 * fs)], btype="bandpass")
    return filtfilt(b, a, x).astype(np.float64)


def _env(x: NDArray[np.float64]) -> NDArray[np.float64]:
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return x
    return np.abs(hilbert(x)).astype(np.float64)


def _fit_log_envelope(t: NDArray[np.float64], e: NDArray[np.float64]) -> tuple[float, float, float]:
    """
    Fit ln(e) = c + m*t  (t is seconds relative to chosen fit start).
    Returns (c, m, r2).
    """
    t = np.asarray(t, dtype=np.float64)
    e = np.asarray(e, dtype=np.float64)

    if t.size < 6:
        return float("nan"), float("nan"), float("nan")

    eps = np.finfo(float).eps
    ln = np.log(np.clip(e, eps, None))

    m, c = np.polyfit(t, ln, 1)
    ln_hat = c + m * t

    ss_res = float(np.sum((ln - ln_hat) ** 2))
    ss_tot = float(np.sum((ln - float(np.mean(ln))) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return float(c), float(m), float(r2)


def _estimate_zeta_envelope_auto(
    y: NDArray[np.float64],
    fs: float,
    *,
    fn_hz: float,
    transient_s: float,
    established_min_s: float,
    established_r2_min: float,
) -> tuple[float, float, float, float, int, int]:
    """
    Pick the earliest established decay start i0 such that the envelope log-fit R² meets the threshold.
    Returns (zeta, r2, c, m, i0_fit, i1_fit) where i0/i1 are indices in y.
    """
    fs = float(fs)
    fn_hz = float(fn_hz)
    y = np.asarray(y, dtype=np.float64)

    n = y.size
    if n < int(0.2 * fs):
        return float("nan"), float("nan"), float("nan"), float("nan"), 0, n

    e = _env(y)

    i1 = n
    i0_floor = int(round(max(0.0, transient_s) * fs))
    i0_min = int(round(max(0.0, established_min_s) * fs))

    # ensure the scan region makes sense
    i0_floor = max(0, min(i0_floor, n - 10))
    i0_min = max(i0_floor, min(i0_min, n - 10))

    # scan candidate starts from floor..min, choose earliest meeting R²
    best: tuple[float, int, float, float, float] | None = None
    step = max(1, int(round(0.005 * fs)))  # 5 ms steps

    for i0 in range(i0_floor, i0_min + 1, step):
        t = (np.arange(i0, i1, dtype=np.float64) - float(i0)) / fs
        c, m, r2 = _fit_log_envelope(t, e[i0:i1])
        if not np.isfinite(r2):
            continue
        if r2 >= established_r2_min:
            best = (r2, i0, c, m, r2)
            break

    # fallback: use i0_min if nothing meets threshold
    if best is None:
        i0 = i0_min
        t = (np.arange(i0, i1, dtype=np.float64) - float(i0)) / fs
        c, m, r2 = _fit_log_envelope(t, e[i0:i1])
        best = (r2, i0, c, m, r2)

    _, i0_fit, c_fit, m_fit, r2_fit = best

    alpha = -m_fit
    omega_n = 2.0 * np.pi * fn_hz
    zeta = alpha / (omega_n + 1e-12)

    return float(zeta), float(r2_fit), float(c_fit), float(m_fit), int(i0_fit), int(i1)

