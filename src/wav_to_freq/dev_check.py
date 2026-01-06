from pathlib import Path

from wav_to_freq.impact_io import prepare_hits
from wav_to_freq.modal import analyze_all_hits
from wav_to_freq.reporting.preprocess import write_preprocess_report
from wav_to_freq.reporting.reporting import write_modal_report

def main():

    ROOT = Path(__file__).resolve().parents[2]  # repo root
    WAV = ROOT / "media" / "hit 251212-2.wav"

    stereo, windows, rep = prepare_hits(
        WAV,
        pre_s=0.05,
        post_s=1.50,
        min_separation_s=0.30,
        threshold_sigma=8.0,
        # hammer_channel=StereoChannel.LEFT,  # optional override; default is auto
    )

    out_dir = ROOT / "out" / "smoke_test"

    write_preprocess_report(
        out_dir,
        stereo=stereo,
        windows=windows,
        report=rep,
        title="WAV preprocessing (smoke test)",
    )

    results = analyze_all_hits(
        windows=windows,
        fs=stereo.fs,
        fmin_hz=1,
        fmax_hz=2000,
    )

    write_modal_report(
        results=results,
        out_dir=out_dir,
        windows=windows,
        fs=stereo.fs,
        title="Smoke test - modal extraction",
    )

if __name__ == "__main__":
    main()
