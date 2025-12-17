from pathlib import Path

from wav_to_freq.impact_io import prepare_hits
from wav_to_freq.reporting.preprocess import write_preprocess_report

ROOT = Path(__file__).resolve().parents[2]   # repo root (…/wav-to-freq)
WAV = ROOT / "media" / "hit 251212-2.wav"

stereo, wins, rep = prepare_hits(
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
    windows=wins,
    report=rep,
    title="WAV preprocessing (smoke test)",
)

print(rep)
print("hammer channel:", stereo.hammer_channel)
print("n windows:", len(wins))
print("report:", art.report_md)
