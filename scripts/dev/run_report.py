from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.pipeline import run_full_report


DEFAULT_WAV = Path("examples/free_plate_260122/media/audio/free_plate_A1H3.wav")
DEFAULT_OUT = Path("build/dev_reports/free_plate_a1h3")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a quick modal report without the TUI."
    )
    parser.add_argument(
        "--wav",
        type=Path,
        default=DEFAULT_WAV,
        help="Path to input WAV file",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory for reports",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Export PDF (requires pandoc)",
    )
    args = parser.parse_args()

    run_full_report(
        args.wav,
        out_dir=args.out,
        hammer_channel=StereoChannel.LEFT,
        export_pdf=args.pdf,
    )

    print(f"Wrote reports to: {args.out}")


if __name__ == "__main__":
    main()
