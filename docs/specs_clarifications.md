# Exhaustive clarification checklist for specs.md

# (Question-only master list)

Status legend (for your own tracking later):

- ⏳ unanswered
- 🟡 partially answered
- ✅ decided

---

## A) Inputs and configuration

### A1) Are you keeping the “2-channel WAV only” assumption, or do you want to support mono files (hammer-only or response-only) later?

✅ Decision: Stereo WAV input only (2 channels required) for now.

### A2) How is channel assignment provided?

- CLI flags?
- TUI selection?
- Config file?

✅ Decision: Channel assignment (hammer vs accelerometer/response) is done by the user in the TUI.

### A3) Do you want the software to refuse to run if the user doesn’t explicitly assign hammer/response channels?

✅ Decision: Yes. Use a widget that requires explicit input; do not run without channel roles being set.

### A4) Should channel roles be persisted in output metadata so re-running doesn’t require re-selection?

✅ Decision / intent:

- Documentation will say “use channel 1 for hammer”
- But the software must provide a way to flip channels if the user did not follow that convention
- Channel mapping should be persisted/logged in outputs so results remain reproducible.

Notes (implication to add to `specs.md` later):

- Pre-process report should show both the *channel index* (L/R or 1/2) and the *semantic role* (hammer/response).
- “Flip channels” should be explicit and recorded.

---

## B) Hit detection contract

### B5) Which signal is used for hit detection?

- Hammer channel only (recommended)
- Response channel
- Either, user-selectable?

✅ Decision: Hammer channel only.

### B6) Define “a hit” in words

- Is it the largest impulse in a region?
- Or every impulse over threshold?

🟡 Partial (intent decided, details to be captured from existing implementation):

- Hit detection is automatic and has worked well.
- Current codebase uses hammer preprocessing + peak detection with a robust threshold.
- Needs to be written as a formal “contract” in `specs.md`:
  - “Hits are peaks in a processed hammer envelope above a robust threshold”
  - “Peaks are detected with prominence and distance constraints”
  - Parameters and defaults are documented (see B7 and future “Detector settings”).

(Implementation reference: current code uses HP + abs + smoothing + MAD threshold + fallback percentile + find_peaks.)

### B7) What is the minimum separation between hits (dead time / lockout)?

✅ Decision:

- Default: 0.30 s
- Must be a tweakable user setting

### B8) Do you want detection to be

- Fully automatic
- Automatic with a “sensitivity” knob
- Manual override (add/remove hits) later?

✅ Decision: Automatic for now. Revisit later if needed for typical structures, but currently works.

### B9) What should happen with double taps / hammer bounce (two close impulses)?

✅ Decision / scope:

- Cropping/excluding hits is a wishlist feature but out-of-scope for now.
- Users can crop/exclude using external tools (e.g., Audacity).
- If a recording is bad, it’s acceptable to redo the measurement (files are short, < 1 min).
Notes:
- The software should make it easy to *diagnose* a bad file quickly (pre-process report).

### B10) Should the app detect and flag

- Missed hits (expected but not found)?
- False positives (noise spikes)?
- “Too many hits” as user error?

✅ Decision: Not required.

- Users may miss hits or vary time between hits; this should not be treated as a problem.
- The tool reports what it found.

---

## C) Time windows per hit

### C11) How do you anchor the hit window?

- At hammer peak time
- Slightly before the peak (pre-trigger)
- Some offset after peak (to avoid saturation)
✅ Decision: Pre-trigger only.

### C12) What is the pre-hit padding (time included before impact), if any?

- No extended quiet baseline in each hit window.
- Baseline/noise estimation is a global pre-process concern, not per-hit window content.
✅ Decision: Anchor is slightly earlier than the detected hit peak (pre-trigger behavior).

### C13) What is the default post-hit duration?

✅ Decision: Fixed duration in seconds + tweakable.

- Default: 1.5 s (keep current codebase default)

### C14) Should post-hit duration be

- Fixed seconds
- Fixed number of samples
- Based on estimated frequency (N cycles)
- Adaptive until energy drops below threshold
- Hybrid (min/max limits)?

✅ Decision: Fixed duration in seconds + tweakable.

- Default: 1.5 s (keep current codebase default)

### C15) If the decay doesn’t finish inside the window, do you

- Compute anyway with flags
- Reject certain methods
- Extend the window if possible?

✅ Decision: Compute anyway, rely on diagnostics/flags.

### C16) Should you support “established decay” cropping inside the hit window?

✅ Decision:  Hybrid

- Both approaches are computed:
  - Full-window analysis (fixed post-hit duration)
  - Established-decay analysis (if a clean decay segment can be identified)
- No method switching:
  - Both results are produced when possible
  - Each result carries its own diagnostics and flags
- Established-decay detection:
  - Is opportunistic, not mandatory
  - Failure to detect an established decay is not an error
- Reporting / reproducibility:
  - Cropping start/end times (relative to hit) must be logged
  - Diagnostics must indicate whether:
    - Established decay was detected
    - Which estimators used it

---

## D) Preprocessing (filtering, detrending, integration)

⏳ Not discussed fully yet (D17 - D23)

### D17) Do you apply baseline removal / detrending to the response before analysis?

- Mean removal
- Linear detrend
- High-pass filter
- None?

✅ Decision:

- Always remove the mean (DC offset) from the response signal
- No linear detrend by default
- No global high-pass filter applied to the response signal

Clarifications:

- DC removal is considered mandatory signal conditioning
- Any additional filtering of the response:
  - must be method-specific (e.g. band-pass around fi)
  - must be explicitly logged
  - must not be applied globally by default

Notes:

- High-pass filtering at preprocessing stage is allowed for the hammer channel only
- Low-frequency content in the response must be preserved for structural modes

### D18) Any anti-aliasing or resampling ever, or assume WAV sample rate is final?

✅ Decision:

- Assume the WAV sample rate is final
- No resampling or anti-aliasing is performed by the software

Clarifications:

- The acquisition device is responsible for anti-aliasing
- The recorded WAV is treated as ground truth
- If the sample rate is inappropriate, the recording is considered invalid input

Notes:

- Any future resampling support must be:
  - explicit
  - user-triggered
  - fully documented and logged

### D19) When doing band-pass filtering around fi

- What filter family is allowed (Butterworth, FIR, etc.)?
- What order constraints exist?

### D20) How is band width chosen?

- Fixed Hz
- Proportional to fi (± x%)
- Based on half-power points

### D21) Do you apply padding/windowing to reduce filter transients?

### D22) For energy methods requiring velocity from acceleration

- Integrate in time or frequency domain?
- How do you control drift / DC offset?
- Do you high-pass before integrating?

### D23) Are you ever allowed to filter the hammer channel, or is it raw-only beyond hit detection?

---

## E) Frequency estimation and peak handling

⏳ Not discussed yet (E24–E30)

### E24) Is peak detection done on

- Per-hit PSD
- PSD averaged across hits
- Both (global list + per-hit refinement)?

### E25) How is the PSD computed?

- Welch parameters fixed or configurable?
- Window type?
- Segment length and overlap?

### E26) How is the noise floor estimated?

- Median
- Percentile
- Smoothed spectrum?

### E27) What defines a valid peak?

- Minimum relative prominence
- Absolute amplitude threshold
- SNR threshold?

### E28) Peak merging rule

- Minimum spacing in Hz
- Minimum spacing as % of fi

### E29) When peaks are close (near-degenerate), do you

- Keep both
- Merge into one
- Mark as a “coupled region”?

### E30) Do you want sub-bin refinement (e.g., quadratic interpolation), or keep bin-centered frequencies?

---

## F) Diagnostics (metrics, thresholds, meaning)

⏳ Not discussed yet (F31–F38)

### F31) For each diagnostic, do you want

- A numeric metric always reported?
- Plus a threshold-based flag?

### F32) Which diagnostics are core (must implement now) vs “nice to have later”?

### F33) Define “SNR estimate” precisely

- Time-domain SNR (impact vs noise window)
- Frequency-domain SNR (peak vs noise floor band)
- Both?

### F34) Beating detection

- What metric is used (envelope modulation depth, spectral splitting, Hilbert envelope peaks)?
- What threshold triggers BEATING_DETECTED?

### F35) Envelope monotonicity

- What test is used (smoothed monotonicity, % of increasing steps, slope sign stability)?

### F36) Instantaneous frequency stability

- How is it computed (Hilbert phase derivative, zero-crossing)?
- What drift threshold triggers INSTANT_FREQ_DRIFT?

### F37) Filter dominance / ringing risk

- What metric distinguishes filter ringing from true decay?

### F38) Sensitivity of ζ to small parameter changes

- Which parameters are perturbed (filter bandwidth, fit range, start time)?
- What sensitivity threshold triggers FILTER_SENSITIVITY_HIGH?

---

## G) Damping estimators (exact procedure + applicability)

⏳ Not discussed yet (G39–G46)

### G39) Time-domain log decrement

- Peaks-to-peaks?
- Envelope fit?
- Linear regression on log envelope?

### G40) Do you use the full window or only the established decay segment?

### G41) Define TOO_SHORT_DECAY

- Minimum number of cycles?
- Minimum number of peaks?

### G42) Half-power bandwidth method

- Use −3 dB points from PSD peak?
- Is smoothing allowed?

### G43) What if half-power points cannot be found cleanly (multi-peak region)?

### G44) Energy decay method

- What exact energy proxy is used (v², a²/ω², integral of squared signal)?

### G45) How do you convert decay rate to ζ (assumed relationship)?

### G46) When do you automatically label EFFECTIVE_DAMPING_ONLY?

---

## H) Status classification rules (OK / WARNING / REJECTED)

⏳ Not discussed yet (H47–H51)

### H47) Do you want a deterministic mapping: diagnostic thresholds → status?

### H48) Are some reason codes always REJECTED (hard failures), while others are WARNING (soft failures)?

### H49) Can multiple reason codes coexist, and is there a priority ordering?

### H50) Do you want a NOT_COMPUTED status for methods that aren’t mathematically possible, distinct from REJECTED?

### H51) Should REJECTED values still show numeric ζ, and should they be excluded from plots/averages by default?

---

## I) “Best guess” policy

⏳ Not discussed yet (I52–I55)

### I52) If multiple OK estimates exist (TD_raw, TD_filt, FD, Energy), which wins?

### I53) Is “best guess” per peak fi or per hit overall?

### I54) Should best guess ever come from the Energy method, or only if no modal method is OK?

### I55) Should best guess prefer

- Consistency across methods
- Consistency across hits
- Lowest sensitivity score?

---

## J) Aggregation across hits

⏳ Not discussed yet (J56–J60)

### J56) How do you group peaks across hits (frequency clustering method)?

### J57) What tolerance defines “same mode” across hits (Hz or %)?

### J58) What summary statistics do you want?

- Mean / median
- Trimmed mean
- Min / max
- Confidence interval?

### J59) Do you want separate aggregates for OK-only vs (OK + WARNING)?

### J60) If some hits have different dominant peaks, do you

- Keep separate mode groups
- Select one “global mode 0”
- Report “multiple mode candidates” only?

---

## K) Reporting: required content and structure

⏳ Not discussed yet (K61–K65)

### K61) Pre-process report: should it include hit count and hit timestamps?

### K62) Per-hit report structure

- One markdown per hit
- One combined markdown with sections?

### K63) Should each hit section include

- Raw hammer + response window plots?
- Filtered response plot per candidate peak?
- PSD plot with annotated peaks?
- Decay/envelope plot per method?

### K64) Do you want machine-readable outputs (JSON / CSV) for database ingestion?

### K65) What is the directory structure contract (filenames, paths) that must not change?

---

## L) Output determinism and reproducibility

⏳ Not discussed yet (L66–L68)

### L66) Which parameters are considered part of the “analysis config” and must be echoed in reports?

### L67) Do you want a version stamp (package version / git hash) inside reports?

### L68) Should random or heuristic behavior be eliminated entirely?

---

## M) Limits and constraints

⏳ Not discussed yet (M69–M71)

### M69) Expected frequency ranges (e.g., 0–30 Hz structures vs 100–1000 Hz bench parts), and should defaults adapt?

### M70) What is the maximum WAV duration you expect (performance constraints)?

### M71) Should the software handle clipped signals gracefully (analyze anyway with flags) or stop?

---

## N) Future-proofing (explicitly out of scope but named)

⏳ Not discussed yet (N72–N74)

### N72) Manual hit editing UI (add/remove hit): planned or not?

### N73) Multi-accelerometer / multi-channel files: planned or never?

### N74) Database integration: should a minimal JSON schema be specified now for future use?
