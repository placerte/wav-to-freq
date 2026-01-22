from __future__ import annotations

import numpy as np

from wav_to_freq.domain.reason_codes import ReasonCode


def compute_filter_risk(
    *,
    fi_hz: float,
    lo_hz: float,
    hi_hz: float,
    q_factor_max: float,
) -> tuple[float, ReasonCode | None]:
    bw_hz = float(hi_hz) - float(lo_hz)
    if bw_hz <= 0:
        return float("nan"), ReasonCode.FILTER_INVALID_BAND

    q_factor = float(fi_hz) / max(bw_hz, np.finfo(float).eps)
    flag = ReasonCode.FILTER_RINGING_RISK if q_factor >= float(q_factor_max) else None
    return q_factor, flag
