from __future__ import annotations

from dataclasses import replace

from wav_to_freq.domain.reason_codes import HARD_FAILURE_CODES, SOFT_FAILURE_CODES
from wav_to_freq.domain.results import EstimateResult
from wav_to_freq.domain.status import EstimateStatus


def assess_estimate(estimate: EstimateResult) -> EstimateResult:
    codes = set(estimate.reason_codes)
    if codes & HARD_FAILURE_CODES:
        if estimate.zeta is None:
            status = EstimateStatus.NOT_COMPUTED
        else:
            status = EstimateStatus.REJECTED
        return replace(estimate, status=status)

    if codes & SOFT_FAILURE_CODES:
        return replace(estimate, status=EstimateStatus.WARNING)

    return replace(estimate, status=EstimateStatus.OK)
