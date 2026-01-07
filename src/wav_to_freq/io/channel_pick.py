import numpy as np
from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.dsp.filters import highpass
from wav_to_freq.dsp.stats import kurtosis_spikiness


def auto_pick_hammer_channel(
    left: np.ndarray, right: np.ndarray, fs: float
) -> tuple[StereoChannel, float, float]:
    # high-pass helps remove low-frequency drift and emphasizes impulse character
    L = highpass(left, fs, fc_hz=200.0)
    R = highpass(right, fs, fc_hz=200.0)

    sL = kurtosis_spikiness(L)
    sR = kurtosis_spikiness(R)

    if sL >= sR:
        ch = StereoChannel.LEFT
    else:
        ch = StereoChannel.RIGHT

    return ch, float(sL), float(sR)
