from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from wav_to_freq.domain.reason_codes import ReasonCode


@dataclass(frozen=True)
class HalfPowerResult:
    zeta: float
    f1_hz: float
    f2_hz: float
    peak_power: float
    reason_codes: tuple[ReasonCode, ...] = ()


def estimate_fd_half_power(
    f_hz: NDArray[np.float64],
    pxx: NDArray[np.float64],
    *,
    peak_hz: float,
    coupled: bool = False,
    peak_detection_count: int | None = None,
    total_hits: int | None = None,
    min_detection_hits: int | None = None,
) -> HalfPowerResult:
    f = np.asarray(f_hz, dtype=np.float64)
    p = np.asarray(pxx, dtype=np.float64)
    if f.size == 0 or p.size == 0 or f.size != p.size:
        return HalfPowerResult(
            zeta=float("nan"),
            f1_hz=float("nan"),
            f2_hz=float("nan"),
            peak_power=float("nan"),
            reason_codes=(ReasonCode.HALF_POWER_NOT_FOUND_LEFT,),
        )

    if coupled:
        return HalfPowerResult(
            zeta=float("nan"),
            f1_hz=float("nan"),
            f2_hz=float("nan"),
            peak_power=float("nan"),
            reason_codes=(ReasonCode.PSD_MULTI_PEAK, ReasonCode.MULTI_MODE_SUSPECTED),
        )

    peak_hz = float(peak_hz)
    idx = int(np.argmin(np.abs(f - peak_hz)))
    peak_power = float(p[idx])
    if not np.isfinite(peak_power) or peak_power <= 0:
        return HalfPowerResult(
            zeta=float("nan"),
            f1_hz=float("nan"),
            f2_hz=float("nan"),
            peak_power=float("nan"),
            reason_codes=(ReasonCode.BAD_ZETA_HP,),
        )

    half_power = 0.5 * peak_power

    left_idx = None
    for i in range(idx - 1, -1, -1):
        if p[i] <= half_power:
            left_idx = i
            break

    if left_idx is None:
        return HalfPowerResult(
            zeta=float("nan"),
            f1_hz=float("nan"),
            f2_hz=float("nan"),
            peak_power=peak_power,
            reason_codes=(ReasonCode.HALF_POWER_NOT_FOUND_LEFT,),
        )

    right_idx = None
    for i in range(idx + 1, p.size):
        if p[i] <= half_power:
            right_idx = i
            break

    if right_idx is None:
        return HalfPowerResult(
            zeta=float("nan"),
            f1_hz=float("nan"),
            f2_hz=float("nan"),
            peak_power=peak_power,
            reason_codes=(ReasonCode.HALF_POWER_NOT_FOUND_RIGHT,),
        )

    f1_hz = _interp_crossing(
        f[left_idx], p[left_idx], f[left_idx + 1], p[left_idx + 1], half_power
    )
    f2_hz = _interp_crossing(
        f[right_idx - 1],
        p[right_idx - 1],
        f[right_idx],
        p[right_idx],
        half_power,
    )

    if not np.isfinite(f1_hz) or not np.isfinite(f2_hz) or f2_hz <= f1_hz:
        return HalfPowerResult(
            zeta=float("nan"),
            f1_hz=float("nan"),
            f2_hz=float("nan"),
            peak_power=peak_power,
            reason_codes=(ReasonCode.BAD_ZETA_HP,),
        )

    zeta = (f2_hz - f1_hz) / (2.0 * peak_hz)
    if not np.isfinite(zeta) or zeta <= 0:
        return HalfPowerResult(
            zeta=float("nan"),
            f1_hz=float("nan"),
            f2_hz=float("nan"),
            peak_power=peak_power,
            reason_codes=(ReasonCode.BAD_ZETA_HP,),
        )

    reason_codes: list[ReasonCode] = []
    if (
        min_detection_hits is not None
        and total_hits
        and peak_detection_count is not None
        and peak_detection_count < min_detection_hits
    ):
        reason_codes.append(ReasonCode.MULTI_MODE_SUSPECTED)

    return HalfPowerResult(
        zeta=float(zeta),
        f1_hz=float(f1_hz),
        f2_hz=float(f2_hz),
        peak_power=peak_power,
        reason_codes=tuple(reason_codes),
    )


def _interp_crossing(
    f0: float, p0: float, f1: float, p1: float, target: float
) -> float:
    if p1 == p0:
        return float(f0)
    t = (target - p0) / (p1 - p0)
    return float(f0 + t * (f1 - f0))
