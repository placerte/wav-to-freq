from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import matplotlib.pyplot as plt

from .impact_io import StereoWav, HitWindow, HitDetectionReport


# -----------------------------
# Small, dependency-free Markdown builder
# -----------------------------

class MarkdownDoc:
    """
    Tiny helper to build Markdown without a pile of brittle string concatenation.
    Keeps report code readable, while staying dependency-free.
    """

    def __init__(self) -> None:
        self._lines: list[str] = []

    def add(self, line: str = "") -> None:
        self._lines.append(line)

    def h1(self, title: str) -> None:
        self.add(f"# {title}")
        self.add()

    def h2(self, title: str) -> None:
        self.add(f"## {title}")
        self.add()

    def h3(self, title: str) -> None:
        self.add(f"### {title}")
        self.add()

    def p(self, text: str) -> None:
        self.add(text)
        self.add()

    def bullet(self, items: Iterable[str]) -> None:
        for it in items:
            self.add(f"- {it}")
        self.add()

    def codeblock(self, code: str, lang: str = "") -> None:
        self.add(f"```{lang}".rstrip())
        self.add(code.rstrip())
        self.add("```")
        self.add()

    def table(self, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        # Simple GitHub-flavored markdown table
        self.add("| " + " | ".join(headers) + " |")
        self.add("| " + " | ".join(["---"] * len(headers)) + " |")
        for r in rows:
            self.add("| " + " | ".join(r) + " |")
        self.add()

    def to_markdown(self) -> str:
        # ensure trailing newline
        return "\n".join(self._lines).rstrip() + "\n"


# -----------------------------
# Plotting helpers
# -----------------------------

def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def plot_hammer_with_hit_markers(
    stereo: StereoWav,
    windows: Sequence[HitWindow],
    out_path: Path,
    *,
    max_seconds: float | None = None,
) -> Path:
    """
    Plot full hammer signal with vertical lines at detected hit times.
    """
    fs = float(stereo.fs)
    hammer = np.asarray(stereo.hammer)
    n = hammer.size

    if max_seconds is None:
        n_plot = n
    else:
        n_plot = int(min(n, max_seconds * fs))

    t = np.arange(n_plot) / fs
    y = hammer[:n_plot]

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(t, y)

    for w in windows:
        if w.hit_index < n_plot:
            ax.axvline(w.hit_index / fs)

    ax.set_title("Hammer signal with detected hits")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_example_window(
    stereo: StereoWav,
    window: HitWindow,
    out_path: Path,
) -> Path:
    """
    Plot one extracted window (hammer + accel) vs time.
    """
    fs = float(stereo.fs)
    hammer = np.asarray(window.hammer)
    accel = np.asarray(window.accel)

    n = min(hammer.size, accel.size)
    t = np.arange(n) / fs

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(t, hammer[:n], label="hammer")
    ax.plot(t, accel[:n], label="accel")
    ax.legend()

    ax.set_title(f"Example extracted hit window (t0={window.t0:.4f}s)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# -----------------------------
# Report generation
# -----------------------------

@dataclass(frozen=True)
class PreprocessReportArtifacts:
    report_md: Path
    fig_hammer_hits: Path
    fig_example_window: Path


def write_preprocess_report(
    out_dir: str | Path,
    *,
    stereo: StereoWav,
    windows: Sequence[HitWindow],
    report: HitDetectionReport,
    title: str = "WAV preprocessing report",
    max_plot_seconds: float | None = None,
) -> PreprocessReportArtifacts:
    """
    Create a markdown report + figures for the preprocessing stage.

    Output structure:
      out_dir/
        report_preprocess.md
        figures/
          hammer_with_hits.png
          example_window.png
    """
    out_dir = _ensure_dir(Path(out_dir))
    fig_dir = _ensure_dir(out_dir / "figures")

    fig_hammer_hits = plot_hammer_with_hit_markers(
        stereo,
        windows,
        fig_dir / "hammer_with_hits.png",
        max_seconds=max_plot_seconds,
    )

    example = windows[0] if len(windows) else None
    fig_example_window = fig_dir / "example_window.png"
    if example is not None:
        plot_example_window(stereo, example, fig_example_window)

    fig_overview = plot_overview_two_channels(
    stereo,
    windows,
    fig_dir / "overview_two_channels.png",
    max_seconds=max_plot_seconds,
)

    md = MarkdownDoc()
    md.h1(title)

    # Section: File / signal specs
    md.h2("WAV file specs")
    duration_s = (len(stereo.hammer) / float(stereo.fs)) if float(stereo.fs) > 0 else float("nan")

    md.table(
        headers=["Field", "Value"],
        rows=[
            ["Path", str(stereo.path)],
            ["Sample rate (Hz)", f"{float(stereo.fs):.3f}"],
            ["Samples", f"{len(stereo.hammer)}"],
            ["Duration (s)", f"{duration_s:.6f}"],
            ["Hammer channel", str(stereo.hammer_channel)],
        ],
    )

    # Section: Hit detection summary
    md.h2("Hit detection summary")
    md.table(
        headers=["Metric", "Value"],
        rows=[
            ["Hits found", str(int(report.n_hits_found))],
            ["Hits used", str(int(report.n_hits_used))],
            ["Threshold (abs)", f"{float(report.threshold):.6g}"],
            ["Min separation (s)", f"{float(report.min_separation_s):.6g}"],
            ["Window pre (s)", f"{float(report.pre_s):.6g}"],
            ["Window post (s)", f"{float(report.post_s):.6g}"],
        ],
    )

    # Section: Raw parameters (nice for traceability)
    md.h2("Raw parameters (traceability)")
    md.codeblock(
        "\n".join(
            [
                f"hammer_channel={stereo.hammer_channel!r}",
                f"n_hits_found={report.n_hits_found}",
                f"n_hits_used={report.n_hits_used}",
                f"threshold={report.threshold}",
                f"min_separation_s={report.min_separation_s}",
                f"pre_s={report.pre_s}",
                f"post_s={report.post_s}",
            ]
        ),
        lang="text",
    )

    md.p("Overview (hammer on top, response on bottom), aligned in time:")
    md.add(f"![overview two channels]({fig_overview.relative_to(out_dir).as_posix()})")
    md.add()

    report_md = out_dir / "report_preprocess.md"
    report_md.write_text(md.to_markdown(), encoding="utf-8")



    return PreprocessReportArtifacts(
        report_md=report_md,
        fig_hammer_hits=fig_hammer_hits,
        fig_example_window=fig_example_window,
    )

def plot_overview_two_channels(
    stereo: StereoWav,
    windows: Sequence[HitWindow],
    out_path: Path,
    *,
    max_seconds: float | None = None,
    show_hit_markers: bool = True,
) -> Path:
    """
    Overview plot (full recording):
      - Top: hammer channel
      - Bottom: response/accel channel
    Both share the same time axis (aligned), with independent y scales.
    """
    fs = float(stereo.fs)

    hammer = np.asarray(stereo.hammer)
    accel = np.asarray(stereo.accel)

    n = min(hammer.size, accel.size)

    if max_seconds is None:
        n_plot = n
    else:
        n_plot = int(min(n, max_seconds * fs))

    t = np.arange(n_plot) / fs

    fig, (ax_h, ax_a) = plt.subplots(
        2, 1,
        sharex=True,
        figsize=(10, 6),
    )

    ax_h.plot(t, hammer[:n_plot])
    ax_h.set_title("Overview (aligned): hammer + response")
    ax_h.set_ylabel("Hammer")

    ax_a.plot(t, accel[:n_plot])
    ax_a.set_ylabel("Response")
    ax_a.set_xlabel("Time (s)")

    if show_hit_markers:
        for w in windows:
            if w.hit_index < n_plot:
                x = w.hit_index / fs
                ax_h.axvline(x)
                ax_a.axvline(x)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path

