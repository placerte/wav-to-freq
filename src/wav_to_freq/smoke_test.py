from pathlib import Path

from wav_to_freq.impact_io import prepare_hits
from wav_to_freq.reporting.preprocess import write_preprocess_report
from wav_to_freq.modal import analyze_all_hits

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

results = analyze_all_hits(wins, stereo.fs)

r0 = results[0]

print("=== HIT 0 MODAL ===")
print("hit_id        :", r0.hit_id)
print("hit_index     :", r0.hit_index)
print("ringdown (s)  :", f"{r0.t0_s:.3f} -> {r0.t1_s:.3f}")
print("fn_hz         :", f"{r0.fn_hz:.3f}")
print("zeta          :", f"{r0.zeta:.5f}")
print("snr_db        :", f"{r0.snr_db:.1f}")
print("env_fit_r2    :", f"{r0.env_fit_r2:.3f}")
print("reject_reason :", r0.reject_reason)
