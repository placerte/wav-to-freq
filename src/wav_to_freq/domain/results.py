from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from wav_to_freq.domain.reason_codes import ReasonCode
from wav_to_freq.domain.status import EstimateStatus


@dataclass(frozen=True)
class DiagnosticValue:
    """One diagnostic metric plus its threshold-triggered flag (optional)."""

    name: str
    value: float | None
    flag: ReasonCode | None = None


@dataclass(frozen=True)
class PeakCandidate:
    """One candidate frequency peak `fi` for a given hit."""

    peak_rank: int  # 1..N within this hit
    fi_bin_hz: float
    fi_refined_hz: float | None = None

    peak_power: float | None = None
    noise_floor: float | None = None
    peak_snr_db: float | None = None

    is_global: bool = True
    reason_codes: tuple[ReasonCode, ...] = ()
    peak_detection_count: int | None = None
    detection_ratio: float | None = None


@dataclass(frozen=True)
class EstimateResult:
    """One estimator output for a (hit, peak_rank) pair."""

    hit_id: int
    peak_rank: int
    method: str

    fi_bin_hz: float
    fi_refined_hz: float | None

    zeta: float | None
    status: EstimateStatus
    reason_codes: tuple[ReasonCode, ...] = ()

    # A flat map of numeric diagnostics (report shows numbers + flags).
    diagnostics: Mapping[str, float | None] = field(default_factory=dict)
