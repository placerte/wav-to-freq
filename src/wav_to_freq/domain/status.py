from __future__ import annotations

from enum import StrEnum


class EstimateStatus(StrEnum):
    """Standard status labels for any computed estimate."""

    OK = "ok"
    WARNING = "warning"
    REJECTED = "rejected"
    NOT_COMPUTED = "not_computed"
