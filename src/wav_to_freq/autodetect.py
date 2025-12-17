from scipy import signal
from dataclasses import dataclass
from wav_to_freq.enums import StereoChannel
from wav_to_freq.signal_utils import EPS, highpass, moving_mean, kurtosis_spikiness
import numpy as np

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
        return hi / (lo +EPS)

def _channel_impulsiveness_score(
    x: np.ndarray,
    fs: float,
    *,
    min_separation_s: float,
) -> float:
    """
    Score a channel for being the hammer channel.

    Key idea for your recordings:
      - hammer: short, concentrated energy near the hit instant (even if lower amplitude)
      - response: larger amplitude but energy spread in time (ringdown)

    We:
      1) high-pass
      2) take abs envelope
      3) find a few very large peaks (quantile threshold)
      4) compute early/late energy ratio around each peak
    """
    xhp = highpass(x, fs, fc_hz=200.0)
    env = np.abs(xhp)

    # mild smoothing so the peak finder doesn't latch onto every oscillation
    smooth = moving_mean(env, int(max(1, round(0.002 * fs))))  # ~2 ms

    # pick only the very top events
    q = float(np.quantile(smooth, 0.995))
    floor = float(np.quantile(smooth, 0.98))
    thr = max(q, floor)

    min_sep = int(max(1, round(min_separation_s * fs)))
    peaks, props = signal.find_peaks(smooth, height=thr, distance=min_sep)

    if peaks.size == 0:
        # fallback: "crest-like" metric on high-passed signal
        rms = float(np.sqrt(np.mean(xhp * xhp)) + EPS)
        num = float(np.quantile(np.abs(xhp), 0.999) + EPS)
        return num / rms

    # energy windows (tuned for impact tests)
    early = int(max(1, round(0.006 * fs)))          # 6 ms
    late0 = int(max(1, round(0.050 * fs)))          # start 50 ms after peak
    late1 = int(max(late0 + 1, round(0.150 * fs)))  # end 150 ms after peak

    ratios: list[float] = []
    n = smooth.size
    for i in peaks[: min(peaks.size, 30)]:
        i = int(i)
        e0 = smooth[i : min(n, i + early)]
        l0 = smooth[min(n, i + late0) : min(n, i + late1)]
        e = float(np.sum(e0) + EPS)
        l = float(np.sum(l0) + EPS)
        ratios.append(e / l)

    # hammer should have a higher median early/late ratio
    return float(np.median(ratios)) if ratios else 0.0


def auto_pick_hammer_channel(left: np.ndarray, right: np.ndarray, fs: float) -> tuple[StereoChannel, float, float]:
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
