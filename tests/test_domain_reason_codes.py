from __future__ import annotations

from wav_to_freq.domain.reason_codes import (
    HARD_FAILURE_CODES,
    SOFT_FAILURE_CODES,
    ReasonCode,
)


def test_reason_codes_are_unique_strings() -> None:
    # This protects the machine output contract: reason codes are stable strings.
    values = [rc.value for rc in ReasonCode]
    assert len(values) == len(set(values))


def test_hard_and_soft_failure_sets_do_not_overlap() -> None:
    overlap = HARD_FAILURE_CODES.intersection(SOFT_FAILURE_CODES)
    assert overlap == set()


def test_effective_damping_only_is_not_a_failure_code() -> None:
    # EFFECTIVE_DAMPING_ONLY is a labeling constraint, not a failure.
    assert ReasonCode.EFFECTIVE_DAMPING_ONLY not in HARD_FAILURE_CODES
    assert ReasonCode.EFFECTIVE_DAMPING_ONLY not in SOFT_FAILURE_CODES


def test_example_expected_codes_exist() -> None:
    # A small smoke test to catch accidental renames.
    assert ReasonCode.PSD_MULTI_PEAK.value == "PSD_MULTI_PEAK"
    assert ReasonCode.BEATING_DETECTED.value == "BEATING_DETECTED"
    assert ReasonCode.TOO_SHORT_DECAY.value == "TOO_SHORT_DECAY"
