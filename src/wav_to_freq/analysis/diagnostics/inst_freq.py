from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.signal import hilbert

from wav_to_freq.domain.reason_codes import ReasonCode


def compute_inst_freq_jitter(
    y_filt: NDArray[np.float64],
    fs: float,
    *,
    transient_s: float,
    inst_freq_rel_jitter_max: float,
) -> tuple[float, float, float, ReasonCode | None]:
    fs = float(fs)
    y = np.asarray(y_filt, dtype=np.float64)
    if y.size < 16:
        return float("nan"), float("nan"), float("nan"), None

    z = hilbert(y)
    phase = np.unwrap(np.angle(z))
    f_inst = (fs / (2.0 * np.pi)) * np.diff(phase)

    i0 = int(round(max(0.0, float(transient_s)) * fs))
    if i0 >= f_inst.size:
        return float("nan"), float("nan"), float("nan"), None
    f_inst = f_inst[i0:]
    if f_inst.size < 8:
        return float("nan"), float("nan"), float("nan"), None

    f_med = float(np.median(f_inst))
    mad = float(np.median(np.abs(f_inst - f_med)))
    f_std = 1.4826 * mad
    jitter = f_std / max(abs(f_med), np.finfo(float).eps)
    flag = (
        ReasonCode.INSTANT_FREQ_DRIFT
        if jitter >= float(inst_freq_rel_jitter_max)
        else None
    )
    return float(f_med), float(f_std), float(jitter), flag
