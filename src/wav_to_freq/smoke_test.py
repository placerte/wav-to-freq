from pathlib import Path

from wav_to_freq.impact_io import prepare_hits
from wav_to_freq.reporting import write_preprocess_report

import soundfile as sf 
import numpy as np
import matplotlib.pyplot as plt

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
print("fig (hits):", art.fig_hammer_hits)
print("fig (window):", art.fig_example_window)

data, fs = sf.read(str(WAV), always_2d=True)
left = data[:, 0]
right = data[:, 1]
t = np.arange(left.size) / fs

fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
ax1.set_yscale("log")
ax2.set_yscale("log")
ax1.plot(t, left);  ax1.set_title("RAW LEFT (data[:,0])")
ax2.plot(t, right); ax2.set_title("RAW RIGHT (data[:,1])")
plt.show()
