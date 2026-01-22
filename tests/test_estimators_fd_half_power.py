from __future__ import annotations

import numpy as np

from wav_to_freq.analysis.estimators.fd_half_power import estimate_fd_half_power
from wav_to_freq.domain.reason_codes import ReasonCode


def test_half_power_flags_coupled() -> None:
    f = np.linspace(0.0, 100.0, 501)
    p = np.ones_like(f)
    p[250] = 10.0

    result = estimate_fd_half_power(f, p, peak_hz=50.0, coupled=True)
    assert ReasonCode.PSD_MULTI_PEAK in result.reason_codes
    assert ReasonCode.MULTI_MODE_SUSPECTED in result.reason_codes


def test_half_power_flags_low_detection_support() -> None:
    f = np.linspace(0.0, 100.0, 501)
    p = np.ones_like(f)
    p[250] = 10.0

    result = estimate_fd_half_power(
        f,
        p,
        peak_hz=50.0,
        coupled=False,
        peak_detection_count=1,
        total_hits=10,
        min_detection_hits=3,
    )
    assert ReasonCode.MULTI_MODE_SUSPECTED in result.reason_codes
