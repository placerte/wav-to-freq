from pathlib import Path
import soundfile as sf
import numpy as np
from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.domain.types import AutoDetectInfo, StereoWav
from wav_to_freq.dsp.stats import as_f64
from wav_to_freq.io.channel_pick import auto_pick_hammer_channel


def read_wav_stereo(path: str | Path) -> tuple[np.ndarray, np.ndarray, float, Path]:
    """
    Read a stereo wav and return (left, right, fs, Path).
    """
    p = Path(path)
    data, fs = sf.read(str(p), always_2d=True)
    if data.shape[1] != 2:
        raise ValueError(f"Expected stereo WAV (2 channels). Got shape={data.shape}")

    left = as_f64(data[:, 0])
    right = as_f64(data[:, 1])
    return left, right, float(fs), p

def load_stereo_wav(
    path: str | Path,
    *,
    hammer_channel: StereoChannel,
) -> StereoWav:
    """
    Load a stereo WAV and return hammer + accel channels.

    If hammer_channel is None:
      pick hammer via an impulsiveness score designed for:
        - small sharp hammer spikes
        - larger long response ringdown
    """
    left, right, fs, p = read_wav_stereo(path)

    autodetect: AutoDetectInfo | None = None

    if hammer_channel is StereoChannel.UNKNOWN:
        picked, score_left, score_right = auto_pick_hammer_channel(left, right, fs)
        hammer_channel = picked
        autodetect = AutoDetectInfo(
            method="kurtosis_hp200",
            score_left=score_left,
            score_right=score_right,
            picked=picked,
        )
    else:
        _validate_channel(hammer_channel)

    if hammer_channel == StereoChannel.LEFT:
        hammer, accel = left, right
    else:
        hammer, accel = right, left

    return StereoWav(
        fs=fs,
        hammer=hammer,
        accel=accel,
        hammer_channel=hammer_channel,
        path=p,
        autodetect=autodetect,
    )

def _validate_channel(ch: StereoChannel) -> None:
    if ch not in (StereoChannel.LEFT, StereoChannel.RIGHT):
        raise ValueError(f"hammer_channel must be 'left' or 'right'. Got {ch!r}")
