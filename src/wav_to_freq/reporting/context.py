from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from wav_to_freq.impact_io import HitDetectionReport, HitWindow, StereoWav


@dataclass(frozen=True)
class PreprocessContext:
    out_dir: Path
    fig_dir: Path
    stereo: StereoWav
    windows: Sequence[HitWindow]
    hit_report: HitDetectionReport
    title: str
    max_plot_seconds: float | None
