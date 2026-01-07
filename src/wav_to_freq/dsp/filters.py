import numpy as np
from scipy import signal
from wav_to_freq.dsp.stats import as_f64

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
