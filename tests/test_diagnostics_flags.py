from __future__ import annotations

import numpy as np

from wav_to_freq.analysis.diagnostics.beating import compute_beating_score
from wav_to_freq.analysis.diagnostics.inst_freq import compute_inst_freq_jitter
from wav_to_freq.analysis.diagnostics.monotonicity import compute_envelope_increase_frac
from wav_to_freq.domain.reason_codes import ReasonCode


def test_beating_detects_modulated_signal() -> None:
    fs = 1000.0
    t = np.arange(0.0, 2.0, 1.0 / fs)
    carrier = np.sin(2.0 * np.pi * 50.0 * t)
    envelope = 1.0 + 0.5 * np.sin(2.0 * np.pi * 2.0 * t)
    y = envelope * carrier

    score, flag = compute_beating_score(
        y,
        fs,
        fi_hz=50.0,
        transient_s=0.0,
        beating_score_max=0.20,
    )
    assert score < 0.20
    assert flag is None

    score, flag = compute_beating_score(
        y,
        fs,
        fi_hz=50.0,
        transient_s=0.0,
        beating_score_max=0.10,
    )
    assert score > 0.10
    assert flag == ReasonCode.BEATING_DETECTED


def test_monotonicity_flags_increasing_envelope() -> None:
    fs = 1000.0
    t = np.arange(0.0, 1.0, 1.0 / fs)
    y = np.sin(2.0 * np.pi * 50.0 * t) * (1.0 + 0.5 * t)

    frac, flag = compute_envelope_increase_frac(
        y,
        fs,
        fi_hz=50.0,
        transient_s=0.0,
        envelope_increase_frac_max=0.10,
    )
    assert frac > 0.10
    assert flag == ReasonCode.ENVELOPE_NON_MONOTONIC


def test_inst_freq_jitter_flags_noisy_phase() -> None:
    fs = 1000.0
    t = np.arange(0.0, 1.0, 1.0 / fs)
    phase = 2.0 * np.pi * 50.0 * t + 0.5 * np.sin(2.0 * np.pi * 10.0 * t)
    y = np.sin(phase)

    _, _, jitter, flag = compute_inst_freq_jitter(
        y,
        fs,
        transient_s=0.0,
        inst_freq_rel_jitter_max=0.05,
    )
    assert jitter >= 0.05
    assert flag == ReasonCode.INSTANT_FREQ_DRIFT
