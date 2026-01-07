from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from wav_to_freq.domain.types import HitDetectionReport, HitWindow, StereoWav


@dataclass(frozen=True)
class PreprocessContext:
    out_dir: Path
    fig_dir: Path
    stereo: StereoWav
    windows: Sequence[HitWindow]
    hit_report: HitDetectionReport
    title: str
    max_plot_seconds: float | None

@dataclass(frozen=True)
class ReportContext:
    out_dir: Path
    fig_dir: Path
    title: str

    def rel(self, path: Path) -> str:
        # markdown-friendly relative path
        return path.relative_to(self.out_dir).as_posix()
