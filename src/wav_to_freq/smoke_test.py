from pathlib import Path

from wav_to_freq.impact_io import prepare_hits
from wav_to_freq.reporting.preprocess import write_preprocess_report
from wav_to_freq.reporting.modal import write_modal_report
from wav_to_freq.modal import analyze_all_hits

ROOT = Path(__file__).resolve().parents[2]   # repo root (…/wav-to-freq)
WAV = ROOT / "media" / "hit 251212-2.wav"

stereo, windows, rep = prepare_hits(
    WAV,
    pre_s=0.05,
    post_s=1.50,
    min_separation_s=0.30,
    threshold_sigma=8.0,
    # hammer_channel="left"
)

out_dir = ROOT / "out" / "smoke_test"
art = write_preprocess_report(
    out_dir,
    stereo=stereo,
    windows=windows,
    report=rep,
    title="WAV preprocessing (smoke test)",
)


results = analyze_all_hits(
    windows=windows,
    fs=stereo.fs,
    fmin_hz= 1,
    fmax_hz= 2000,
)

art = write_modal_report(
    out_dir=out_dir,
    stereo=stereo,
    windows=windows,
    hit_report=rep,
    modal_results=results,
    title="Smoke test - modal extraction"
    )

