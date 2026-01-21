from __future__ import annotations

from wav_to_freq.domain.status import EstimateStatus


def test_estimate_status_values_are_stable() -> None:
    # These strings may appear in CSV/JSON outputs; treat as stable API.
    assert EstimateStatus.OK.value == "ok"
    assert EstimateStatus.WARNING.value == "warning"
    assert EstimateStatus.REJECTED.value == "rejected"
    assert EstimateStatus.NOT_COMPUTED.value == "not_computed"
