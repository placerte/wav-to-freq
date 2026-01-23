from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.signal import hilbert
from typing import cast

from wav_to_freq.domain.reason_codes import ReasonCode


def compute_beating_score(
    y_filt: NDArray[np.float64],
    fs: float,
    *,
    fi_hz: float,
    transient_s: float,
    beating_score_max: float,
) -> tuple[float, ReasonCode | None]:
    fs = float(fs)
    fi_hz = float(fi_hz)
    y = np.asarray(y_filt, dtype=np.float64)
    if y.size < 8:
        return float("nan"), None

    result = hilbert(y)
    if result is None:
        return float("nan"), None
    if isinstance(result, tuple):
        result = result[0]
    result = cast(NDArray[np.complex128], result)
    env = np.abs(np.asarray(result, dtype=np.complex128)).astype(np.float64)
    i0 = int(round(max(0.0, float(transient_s)) * fs))
    env = env[i0:]
    if env.size < 8:
        return float("nan"), None

    residual = _log_residual(env, fs=fs)
    if residual is None:
        trend = _trend_envelope(env, fs=fs, fi_hz=fi_hz)
        eps = np.finfo(float).eps
        rel = (env - trend) / np.maximum(trend, eps)
        score = float(np.sqrt(np.mean(rel**2)))
    else:
        score = float(np.sqrt(np.mean(residual**2)))
    flag = ReasonCode.BEATING_DETECTED if score >= float(beating_score_max) else None
    return score, flag


def _trend_envelope(
    env: NDArray[np.float64], *, fs: float, fi_hz: float
) -> NDArray[np.float64]:
    window_s = max(0.05, 5.0 / max(float(fi_hz), 1.0))
    n = max(5, int(round(window_s * float(fs))))
    if n % 2 == 0:
        n += 1
    kernel = np.ones(n, dtype=np.float64) / float(n)
    return np.asarray(np.convolve(env, kernel, mode="same"), dtype=np.float64)


def _log_residual(
    env: NDArray[np.float64], *, fs: float
) -> NDArray[np.floating] | None:
    if env.size < 8:
        return None
    eps = np.finfo(float).eps
    t = np.arange(env.size, dtype=np.float64) / float(fs)
    ln = np.log(np.clip(env, eps, None))
    try:
        m, c = np.polyfit(t, ln, 1)
    except np.linalg.LinAlgError:
        return None
    residual = ln - (c + m * t)
    return np.asarray(residual, dtype=np.float64)
