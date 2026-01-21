from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from wav_to_freq.domain.reason_codes import ReasonCode
from wav_to_freq.domain.results import PeakCandidate


def _spacing_hz(fi_hz: float, *, abs_hz: float, frac: float) -> float:
    return max(float(abs_hz), float(frac) * float(fi_hz))


def merge_near_duplicate_peaks(
    peaks: Iterable[PeakCandidate], *, abs_hz: float, frac: float
) -> list[PeakCandidate]:
    """Merge near-duplicate peaks (E28).

    Peaks are grouped by proximity. Within each group, keep the strongest peak.
    Strength is approximated by peak_snr_db, then peak_power.
    """

    peaks_sorted = sorted(peaks, key=lambda p: float(p.fi_bin_hz))
    if not peaks_sorted:
        return []

    groups: list[list[PeakCandidate]] = [[peaks_sorted[0]]]
    for p in peaks_sorted[1:]:
        last = groups[-1][-1]
        tol = _spacing_hz(last.fi_bin_hz, abs_hz=abs_hz, frac=frac)
        if abs(float(p.fi_bin_hz) - float(last.fi_bin_hz)) <= tol:
            groups[-1].append(p)
        else:
            groups.append([p])

    merged: list[PeakCandidate] = []
    for grp in groups:
        if len(grp) == 1:
            merged.append(grp[0])
            continue

        def _strength_key(x: PeakCandidate) -> tuple[float, float]:
            snr = -1e300 if x.peak_snr_db is None else float(x.peak_snr_db)
            pwr = -1e300 if x.peak_power is None else float(x.peak_power)
            return snr, pwr

        best = max(grp, key=_strength_key)
        merged.append(best)

    return merged


def flag_coupled_regions(
    peaks: Iterable[PeakCandidate], *, abs_hz: float, frac: float
) -> list[PeakCandidate]:
    """Mark near-degenerate peaks as coupled (E29) without merging."""

    peaks_sorted = sorted(peaks, key=lambda p: float(p.fi_bin_hz))
    if len(peaks_sorted) < 2:
        return peaks_sorted

    coupled_indices: set[int] = set()
    for i in range(len(peaks_sorted) - 1):
        a = peaks_sorted[i]
        b = peaks_sorted[i + 1]
        tol = _spacing_hz(a.fi_bin_hz, abs_hz=abs_hz, frac=frac)
        if abs(float(b.fi_bin_hz) - float(a.fi_bin_hz)) <= tol:
            coupled_indices.add(i)
            coupled_indices.add(i + 1)

    out: list[PeakCandidate] = []
    for i, p in enumerate(peaks_sorted):
        if i not in coupled_indices:
            out.append(p)
            continue

        codes = set(p.reason_codes)
        codes.add(ReasonCode.PSD_MULTI_PEAK)
        codes.add(ReasonCode.MULTI_MODE_SUSPECTED)
        out.append(replace(p, reason_codes=tuple(sorted(codes))))

    return out
