import numpy as np
from scipy import signal
from wav_to_freq.domain.config import EPS


def as_f64(x: np.ndarray) -> np.ndarray:
    return np.asarray(x, dtype=np.float64)


def moving_mean(x: np.ndarray, win: int) -> np.ndarray:
    """Fast moving average using convolution. win must be >= 1."""
    x = as_f64(x)
    if win <= 1:
        return x
    k = np.ones(int(win), dtype=np.float64) / float(win)
    return np.convolve(x, k, mode="same")


def robust_sigma_mad(x: np.ndarray) -> float:
    """Robust sigma estimate based on MAD."""
    x = as_f64(x)
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med)) + EPS)
    return 1.4826 * mad




def kurtosis_spikiness(x: np.ndarray) -> float:
    """
    Kurtosis (non-fisher): E[(x-mu)^4] / (E[(x-mu)^2]^2)
    Bigger => more "spiky"/impulsive.
    """
    x = np.asarray(x, dtype=np.float64)
    x = x - float(np.mean(x))
    m2 = float(np.mean(x * x)) + 1e-30
    m4 = float(np.mean((x * x) * (x * x))) + 1e-30
    return m4 / (m2 * m2)
