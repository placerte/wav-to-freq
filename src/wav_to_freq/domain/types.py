from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from wav_to_freq.domain.config import EPS
from wav_to_freq.domain.enums import StereoChannel


@dataclass
class AutoDetectInfo:
    method: str
    score_left: float
    score_right: float
    picked: StereoChannel

    @property
    def confidence_hi_lo(self) -> float:
        lo = min(self.score_left, self.score_right)
        hi = max(self.score_left, self.score_right)
        return hi / (lo + EPS)


@dataclass(frozen=True)
class StereoWav:
    """Raw stereo acquisition: hammer + response in the same WAV."""

    fs: float
    hammer: np.ndarray
    accel: np.ndarray
    path: Path
    autodetect: AutoDetectInfo | None = None
    hammer_channel: StereoChannel = StereoChannel.UNKNOWN


@dataclass(frozen=True)
class HitWindow:
    """One extracted hit window, aligned on the detected impact peak."""

    hit_id: int  # 1-based
    hit_index: int  # sample index in the full signal

    t_hit: float  # seconds
    t_start: float  # seconds
    t_end: float  # seconds

    hammer: np.ndarray  # windowed hammer samples
    accel: np.ndarray  # windowed accel samples


@dataclass(frozen=True)
class HitDetectionReport:
    n_hits_found: int
    n_hits_used: int
    threshold: float
    min_separation_s: float
    pre_s: float
    post_s: float


@dataclass(frozen=True)
class HitModalResult:
    hit_id: int
    hit_index: int
    t0_s: float
    t1_s: float
    fn_hz: float
    zeta: float
    snr_db: float
    env_fit_r2: float
    env_log_c: float
    env_log_m: float
    reject_reason: Optional[str] = None
    fit_t0_s: float | None = None
    fit_t1_s: float | None = None
