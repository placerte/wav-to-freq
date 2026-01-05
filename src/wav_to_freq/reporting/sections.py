# ==== FILE: src/wav_to_freq/reporting/sections.py ====

from __future__ import annotations

from wav_to_freq.reporting.markdown import MarkdownDoc
from wav_to_freq.reporting.context import PreprocessContext


def add_section_wav_specs(mdd: MarkdownDoc, context: PreprocessContext) -> None:
    stereo = context.stereo

    mdd.h2("WAV file specs")
    duration_s = (len(stereo.hammer) / float(stereo.fs)) if float(stereo.fs) > 0 else float("nan")

    rows: list[list[str]] = [
        ["Path", str(stereo.path)],
        ["Sample rate (Hz)", f"{float(stereo.fs):.3f}"],
        ["Samples", f"{len(stereo.hammer)}"],
        ["Duration (s)", f"{duration_s:.6f}"],
        ["Hammer channel", str(stereo.hammer_channel)],
    ]

    if stereo.autodetect is not None:
        rows.append(["Autodetect method", stereo.autodetect.method])
        rows.append(["Autodetect score (left)", f"{stereo.autodetect.score_left:.6g}"])
        rows.append(["Autodetect score (right)", f"{stereo.autodetect.score_right:.6g}"])
        rows.append(["Autodetect confidence hi/lo", f"{stereo.autodetect.confidence_hi_lo:.3g}"])

    mdd.table(headers=["Field", "Value"], rows=rows)

