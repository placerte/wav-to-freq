from __future__ import annotations

import numpy as np

from wav_to_freq.analysis.peaks.noise_floor import compute_noise_floor_percentile


def test_noise_floor_percentile_basic() -> None:
    pxx = np.asarray([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    assert compute_noise_floor_percentile(pxx, percentile=50.0) == 2.5


def test_noise_floor_percentile_empty_is_nan() -> None:
    pxx = np.asarray([], dtype=np.float64)
    assert np.isnan(compute_noise_floor_percentile(pxx, percentile=60.0))
