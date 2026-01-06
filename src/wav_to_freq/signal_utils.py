import numpy as np
from scipy import signal

# Epsilon value to avoid dividing bu zero
EPS = 1e-30


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


def highpass(
    x: np.ndarray, fs: float, fc_hz: float = 200.0, order: int = 4
) -> np.ndarray:
    """
    High-pass filter to emphasize the hammer impulse vs the long ringdown.
    fc_hz=200 Hz is a decent default for typical impact testing recordings.
    """
    x = as_f64(x)
    nyq = 0.5 * fs
    fc = max(1.0, min(fc_hz, 0.45 * nyq))
    sos = signal.butter(order, fc / nyq, btype="highpass", output="sos")
    return signal.sosfiltfilt(sos, x)


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
