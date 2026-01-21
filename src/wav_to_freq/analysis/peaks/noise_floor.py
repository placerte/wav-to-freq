from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def compute_noise_floor_percentile(
    pxx_band: NDArray[np.float64], *, percentile: float
) -> float:
    """Compute the PSD noise floor from a percentile (E26)."""

    pp = np.asarray(pxx_band, dtype=np.float64)
    if pp.size == 0:
        return float("nan")
    q = float(percentile)
    if not (0.0 <= q <= 100.0):
        raise ValueError(f"percentile must be in [0, 100]. Got {q}")
    return float(np.percentile(pp, q))
