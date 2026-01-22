from __future__ import annotations

from enum import StrEnum


class ReasonCode(StrEnum):
    """Stable reason/flag codes used in reports and machine outputs."""

    # signal / acquisition quality
    SNR_LOW = "SNR_LOW"
    CLIPPED_SIGNAL = "CLIPPED_SIGNAL"

    # peak / modal purity
    NO_VALID_PEAKS = "NO_VALID_PEAKS"
    PSD_MULTI_PEAK = "PSD_MULTI_PEAK"
    MULTI_MODE_SUSPECTED = "MULTI_MODE_SUSPECTED"

    # time-domain validity
    BEATING_DETECTED = "BEATING_DETECTED"
    ENVELOPE_NON_MONOTONIC = "ENVELOPE_NON_MONOTONIC"
    INSTANT_FREQ_DRIFT = "INSTANT_FREQ_DRIFT"
    TOO_SHORT_DECAY = "TOO_SHORT_DECAY"

    # filtering
    FILTER_INVALID_BAND = "FILTER_INVALID_BAND"
    FILTER_DESIGN_FAILED = "FILTER_DESIGN_FAILED"
    FILTER_RINGING_RISK = "FILTER_RINGING_RISK"

    # FD half-power
    HALF_POWER_NOT_FOUND_LEFT = "HALF_POWER_NOT_FOUND_LEFT"
    HALF_POWER_NOT_FOUND_RIGHT = "HALF_POWER_NOT_FOUND_RIGHT"
    HALF_POWER_AMBIGUOUS = "HALF_POWER_AMBIGUOUS"
    BAD_ZETA_HP = "BAD_ZETA_HP"
    BAD_ZETA_ENERGY = "BAD_ZETA_ENERGY"

    # method labeling
    EFFECTIVE_DAMPING_ONLY = "EFFECTIVE_DAMPING_ONLY"


# v1 baseline classification (H48). These sets may be refined later.
HARD_FAILURE_CODES: set[ReasonCode] = {
    ReasonCode.NO_VALID_PEAKS,
    ReasonCode.TOO_SHORT_DECAY,
    ReasonCode.FILTER_INVALID_BAND,
    ReasonCode.FILTER_DESIGN_FAILED,
    ReasonCode.HALF_POWER_NOT_FOUND_LEFT,
    ReasonCode.HALF_POWER_NOT_FOUND_RIGHT,
    ReasonCode.HALF_POWER_AMBIGUOUS,
    ReasonCode.BAD_ZETA_HP,
    ReasonCode.BAD_ZETA_ENERGY,
}

SOFT_FAILURE_CODES: set[ReasonCode] = {
    ReasonCode.SNR_LOW,
    ReasonCode.CLIPPED_SIGNAL,
    ReasonCode.PSD_MULTI_PEAK,
    ReasonCode.MULTI_MODE_SUSPECTED,
    ReasonCode.BEATING_DETECTED,
    ReasonCode.ENVELOPE_NON_MONOTONIC,
    ReasonCode.INSTANT_FREQ_DRIFT,
    ReasonCode.FILTER_RINGING_RISK,
}
