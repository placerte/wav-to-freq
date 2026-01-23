# Exhaustive clarification checklist for specs.md

# (Question-only master list)

Status legend (for your own tracking later):

- ⏳ unanswered
- 🟡 partially answered
- ✅ decided

---

## Implementation notes (2026-01-23)

These are non-normative notes capturing the current state of the rewrite.

- Multi-estimator damping outputs are now produced per (hit, peak): TD envelope (full + established), FD half-power, and energy-decay (effective) with flags/reason codes.
- Modal report layout now follows `docs/report_layout.md` (hit -> peak -> method), and includes method-specific diagnostic plots intended to make `zeta` values auditable.
- PDF export prefers a LaTeX renderer (`pdflatex`) and falls back to HTML/WeasyPrint.

Known gaps / follow-ups:

- Hit-level PSD plot peak annotations should be sourced from the same peak list used for estimation (avoid plot-only peak picking).
- TD/Energy diagnostic plots should use the exact fit window indices used by the estimator (currently inferred from fit durations).

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

✅ Decision:

- Default filter for per-peak isolation is an IIR Butterworth band-pass.
- Implementation: order 4, applied with zero-phase filtering (e.g. `filtfilt`).
- The cutoff selection rule (lo/hi around `fi`) is defined in D20.
- Validity constraints:
  - Must satisfy `0 < lo_hz < hi_hz < 0.5 * fs` (with a small safety margin from DC/Nyquist).
  - If the design is invalid (e.g. hi <= lo) or the filter application fails, the estimator MUST:
    - not silently continue as if filtered,
    - proceed unfiltered OR return NOT_COMPUTED (implementation choice),
    - and attach a reason code such as `FILTER_INVALID_BAND` or `FILTER_DESIGN_FAILED`.
- Reproducibility: every estimate that uses a band-pass MUST log:
  - filter_family, filter_order, zero_phase (true/false), lo_hz, hi_hz.

### D20) How is band width chosen?

- Fixed Hz
- Proportional to fi (± x%)
- Based on half-power points

✅ Decision:

- Default band selection is proportional to the target peak frequency `fi` (keep current code behavior):
  - `lo0_hz = 0.60 * fi`
  - `hi0_hz = 1.40 * fi`
- The final band MUST be clamped to valid digital filter limits and user-defined analysis bounds:
  - Must satisfy `0 < lo_hz < hi_hz < 0.5 * fs` (with a small safety margin from DC/Nyquist).
  - Must respect the configured modal search band: `lo_hz >= fmin_hz` and `hi_hz <= fmax_hz`.
- Coupled / multi-peak guardrail (to reduce accidental mixing):
  - When a list of candidate peaks is available for the same hit, the band-pass for peak `fi` SHOULD be limited so it does not cross into adjacent peaks:
    - `hi_hz <= 0.5 * (fi + fi_next)` when `fi_next` exists
    - `lo_hz >= 0.5 * (fi_prev + fi)` when `fi_prev` exists
  - If guardrailing collapses the band (`hi_hz <= lo_hz`), the estimator MUST be marked NOT_COMPUTED (or REJECTED) with a reason code such as `PSD_MULTI_PEAK` and/or `FILTER_INVALID_BAND`.
- Reproducibility: every estimate that uses a band-pass MUST log both:
  - the proposal: `lo0_hz`, `hi0_hz`
  - the applied band: `lo_hz`, `hi_hz`, and whether adjacent-peak guardrailing modified it.

### D21) Do you apply padding/windowing to reduce filter transients?

✅ Decision:

- No explicit padding/windowing/tapering is applied by default to reduce band-pass filter transients.
- The default strategy is to use zero-phase filtering (`filtfilt`) and handle edge/transient contamination via analysis window rules:
  - Damping fit MUST start after a configurable transient skip (`transient_s`).
  - If the signal segment is too short to apply `filtfilt` safely (padding requirements) or filtering fails, the estimator MUST be NOT_COMPUTED (or REJECTED) with a reason code such as `TOO_SHORT_DECAY` and/or `FILTER_DESIGN_FAILED`.
- Reproducibility: every estimate MUST log whether band-pass filtering was applied, and the transient skip used for the fit (`transient_s` and the actual fit start time/index).

### D22) For energy methods requiring velocity from acceleration

- Integrate in time or frequency domain?
- How do you control drift / DC offset?
- Do you high-pass before integrating?

✅ Decision:

- The Energy Decay estimator is allowed and is explicitly treated as an **effective damping** method (see reason code `EFFECTIVE_DAMPING_ONLY` in specs).
- Implementation strategy (v1): avoid fragile velocity integration unless explicitly needed.
  - Default energy proxy: use a band-limited response around the target peak `fi` (per D19/D20) and compute an energy-like envelope proxy (e.g. `E(t) ~ env(t)^2` or `E(t) ~ y(t)^2` after band-pass), then fit an exponential decay rate.
  - Velocity-based proxy (optional, not default): if a velocity proxy is required, integration is performed in the **time domain**.
- Drift / DC control requirements:
  - Always remove the mean (DC) before computing any energy proxy.
  - If time-domain integration is used:
    - Apply a high-pass filter before integration to reduce drift (cutoff MUST be logged; default is conservative and mode-aware, e.g. a small fraction of `fi`).
    - After integration, remove any residual mean/drift (at minimum mean removal; optional linear detrend if needed).
  - Frequency-domain integration is out of scope for v1.
- Reproducibility: every Energy estimate MUST log:
  - which proxy was used (`energy_proxy = envelope_sq | signal_sq | velocity_sq`),
  - whether integration was used, the high-pass cutoff (if any),
  - and the exact fit window (start/end times or indices).

### D23) Are you ever allowed to filter the hammer channel, or is it raw-only beyond hit detection?

✅ Decision:

- The hammer channel MAY be filtered/processed for the purpose of **hit detection only**.
  - This includes operations such as high-pass filtering, rectification (abs/polarity), smoothing, normalization, and thresholding.
- The hammer channel MUST NOT be filtered or otherwise conditioned for modal parameter estimation.
  - Modal analysis is performed on the response channel; any filtering applied there must follow D17 and D19–D21.
- Reporting / reproducibility:
  - Preprocess reporting MUST present the raw hammer channel.
  - The detection-processed hammer signal MAY be included as an optional diagnostic, but it must be clearly labeled as such.
  - Hit detection parameters and any hammer preprocessing steps used for detection MUST be logged in outputs.

---

## E) Frequency estimation and peak handling

⏳ Not discussed yet (E24–E30)

### E24) Is peak detection done on

- Per-hit PSD
- PSD averaged across hits
- Both (global list + per-hit refinement)?

✅ Decision:

- Peak detection SHALL use **both** approaches:
  - A robust global spectrum across hits (e.g. median/mean of per-hit PSDs) is used to form a stable list of candidate peak frequencies.
  - Per-hit PSDs are still computed and used to refine/validate peaks on each hit.
  - Add a low-frequency global pass (default 1–100 Hz, 3 dB min peak SNR) merged into the main list before de-duplication, to preserve low-frequency structural modes that may be weaker in the full-band ranking.
  - Optionally add a hit-local union pass: retain peaks that appear in at least `min_hits` hits (default 2) even if they are weak in the median PSD; default hit-local SNR gate is 3 dB with separate SNR/cap settings.
  - When hit-local aggregation is enabled, include a peak detection count and optional detection ratio per global peak for traceability.
- Contract:
  - The analysis MUST produce a per-hit PSD for diagnostics and per-hit peak context.
  - The analysis MUST produce a global candidate-peak list (frequency + basic peak metrics) that is consistent across hits.
  - For each hit, each global candidate peak SHALL be searched/refined locally in that hit (within a small neighborhood) and either confirmed or marked absent/weak.
  - Peaks that appear strongly in a single hit but are not present in the global list MAY be included as additional per-hit candidates, but must be explicitly labeled as hit-local (not globally repeatable).
- Reproducibility: the reports/outputs MUST log whether peaks came from the global list or were hit-local, and the PSD method/config used (see E25).

### E25) How is the PSD computed?

- Welch parameters fixed or configurable?
- Window type?
- Segment length and overlap?

✅ Decision:

- PSD method: Welch PSD (scipy.signal.welch equivalent) is the default and reference implementation.
- Parameters are configurable, but MUST have documented defaults and MUST be logged in outputs.

Default settings (v1):

- Window: Hann
- Detrend: constant (remove mean)
- Overlap: 50% (noverlap = nperseg/2)
- Scaling: density

Segment length / resolution policy:

- The primary user-facing knob is a target frequency resolution `psd_df_target_hz`.
- The implementation chooses `nperseg` deterministically from `psd_df_target_hz` and available samples:
  - Compute `n_target = round(fs / psd_df_target_hz)`
  - Clamp to `[psd_nperseg_min, psd_nperseg_max]` and to `<= len(x)`
  - Optionally snap to a power-of-two for FFT efficiency
- The actual achieved resolution `psd_df_hz = fs / nperseg` MUST be logged.

Preset defaults (initial proposals):

- Structures preset: `psd_df_target_hz = 0.25` (favor separating close low-frequency peaks)
- Xylophone preset: `psd_df_target_hz = 2.0` (coarser is acceptable; faster and robust)

User guidance (must be documented in UI/help):

- If close peaks are not resolved (coupled/multi-mode), decrease `psd_df_target_hz` and/or increase `ring_s` so a longer segment is available.
- If the spectrum is too noisy/peaky, increase overlap, increase averaging (more segments), or slightly increase `psd_df_target_hz`.

Reproducibility:

- Both the per-hit PSDs and any global (across-hits) PSD used for peak selection MUST use the same logged PSD configuration.

### E26) How is the noise floor estimated?

- Median
- Percentile
- Smoothed spectrum?

✅ Decision:

- Noise floor estimation is required for robust peak detection and diagnostics.
- Default (v1): percentile-based noise floor computed from PSD values within the configured analysis band.
  - Define `noise_floor = percentile(Pxx_band, q)`.
  - Default percentile: `q = 60` (robust to outliers while remaining conservative in peaky spectra).
  - The percentile `q` MUST be configurable.
- The noise floor value (and `q`) MUST be logged for both per-hit PSDs and the global (across-hits) PSD.
- The noise floor is used to define peak validity and SNR-like metrics (see E27).

### E27) What defines a valid peak?

- Minimum relative prominence
- Absolute amplitude threshold
- SNR threshold?

✅ Decision:

- A valid PSD peak is defined primarily by an SNR-like threshold relative to the estimated noise floor (see E26).
- Peak SNR definition:
  - `peak_snr_db = 10 * log10(peak_power / noise_floor)`
  - `peak_power` is the PSD value at the peak bin (or locally-refined peak location).
- Validity rule (v1 baseline): a peak is valid iff `peak_snr_db >= min_peak_snr_db`.
  - Default: `min_peak_snr_db = 6.0 dB` (configurable).
- Candidate list behavior:
  - The analysis SHOULD retain up to `max_candidate_peaks` valid peaks per spectrum.
  - Default: `max_candidate_peaks = 5` (configurable).
  - If no peaks meet the threshold, the hit MUST be marked as having no valid peaks (reason code such as `SNR_LOW` or `NO_VALID_PEAKS`).
- Reporting:
  - For each reported peak, outputs MUST include `fi`, `peak_power`, `noise_floor`, and `peak_snr_db`.
  - Any peak that is detected but fails the validity rule MAY be reported for diagnostics but must be marked invalid.

Notes:

- Prominence-based rules are deferred; they may be added later as a refinement once the SNR-based baseline is validated.

### E28) Peak merging rule

- Minimum spacing in Hz
- Minimum spacing as % of fi

✅ Decision:

- A peak merging / de-duplication step is required once multiple candidate peaks are detected.
- Merging rule (v1): use a hybrid minimum spacing that scales with frequency:
  - Define `min_spacing_hz(fi) = max(psd_peak_min_spacing_hz, psd_peak_min_spacing_frac * fi)`.
  - Peaks closer than `min_spacing_hz` are considered part of the same peak group.
- Within each peak group, keep the single strongest peak as the representative.
  - Strength default: highest `peak_snr_db` (tie-breaker: highest `peak_power`).
  - Discarded peaks MAY still be reported as merged-for-diagnostics, but must not be treated as independent candidates.
- Preset default proposals:
  - Structures: `psd_peak_min_spacing_hz = 0.5`, `psd_peak_min_spacing_frac = 0.03`
  - Xylophone: `psd_peak_min_spacing_hz = 5.0`, `psd_peak_min_spacing_frac = 0.01`
- Reproducibility:
  - Outputs MUST log the spacing parameters used and the final peak groups (e.g. which raw peaks were merged into each representative peak).

### E29) When peaks are close (near-degenerate), do you

- Keep both
- Merge into one
- Mark as a “coupled region”?

✅ Decision:

- When peaks are close (near-degenerate), the tool MUST prefer "show the thing":
  - Keep both peaks as separate candidates (do not merge them into a single frequency).
  - Mark the peak pair/group as a coupled / multi-peak region in diagnostics.
- The report MUST:
  - display the close peak frequencies and their PSD metrics,
  - attach reason/flag codes such as `PSD_MULTI_PEAK` and/or `MULTI_MODE_SUSPECTED`.
- Damping behavior:
  - Modal damping estimators (TD/FD) MAY be computed per-peak but MUST be flagged WARNING/REJECTED when their assumptions are violated (e.g. beating, non-monotonic envelope).
  - An Energy/effective damping estimate SHOULD be computed and labeled `EFFECTIVE_DAMPING_ONLY` when coupling is suspected.

### E30) Do you want sub-bin refinement (e.g., quadratic interpolation), or keep bin-centered frequencies?

✅ Decision:

- Sub-bin frequency refinement is allowed and is enabled by default when the peak is eligible.
- Eligibility (conservative): refinement SHOULD be applied only when the peak is isolated (i.e. not part of a coupled/multi-peak region per E29) and has acceptable quality (e.g. sufficient peak SNR).
- Default refinement method (v1): simple deterministic 3-point quadratic interpolation around the PSD peak bin.
  - This may be performed on PSD in linear scale or on log(PSD); the chosen convention MUST be documented and logged.
- Reproducibility / reporting:
  - Outputs MUST log the raw bin-centered frequency (`fn_bin_hz`) and the refined frequency (`fn_refined_hz`) when computed.
  - Outputs MUST log the refinement method (`refinement_method = quadratic_3pt | none`) and whether refinement was skipped due to coupling/quality.

---

## F) Diagnostics (metrics, thresholds, meaning)

⏳ Not discussed yet (F31–F38)

### F31) For each diagnostic, do you want

- A numeric metric always reported?
- Plus a threshold-based flag?

✅ Decision:

- Diagnostics MUST be reported as both:
  - a numeric metric (always reported when computable), and
  - a threshold-/rule-based flag (reason code) shown alongside it.
- The report SHOULD display diagnostics in a way that makes the relationship obvious (e.g. "beating_score=0.37 → `BEATING_DETECTED`"), and SHOULD show "not computed" explicitly when a metric cannot be computed.
- Thresholds used to generate flags MUST be configurable (advanced settings) and MUST be logged in outputs for reproducibility.

### F32) Which diagnostics are core (must implement now) vs “nice to have later”?

✅ Decision:

Priorities (field-first):

1) On-site confirmation that the measured signal is usable (fast go/no-go)
2) Diagnostics on the quality/validity of computed `fn` and `ζ`
3) Other diagnostics (deeper research / nice-to-have)

Core diagnostics (implement now):

- Signal acquisition / data quality (on-site go/no-go):
  - `CLIPPED_SIGNAL` (per channel) + a numeric clipping metric (e.g. fraction of samples at/near full-scale)
  - Hit detection sanity: `n_hits_found`, `n_hits_used`, hit timestamps, and `HIT_COUNT_SUSPICIOUS` (optional)
  - Hammer channel quality for detection: threshold value, baseline noise estimate, and hit prominence / peak SNR-like metric
  - Response channel noise floor estimate and an overall response SNR-like metric for each hit
  - Channel role traceability: which channel was hammer/response + autodetect confidence (if applicable)

- Frequency / peak quality (supports coupled-mode hurdle):
  - `peak_snr_db` per candidate peak (E26/E27)
  - `PSD_MULTI_PEAK` / coupled-region indicator + a numeric proximity metric (e.g. nearest-neighbor spacing in Hz and %)
  - Peak list stability across hits (global vs hit-local peak flag; E24)

- Damping / fit validity:
  - Envelope fit quality (e.g. `env_fit_r2`) with thresholds for WARNING/REJECTED
  - `BEATING_DETECTED` + numeric beating/amplitude-modulation score
  - `ENVELOPE_NON_MONOTONIC` + numeric monotonicity score
  - `TOO_SHORT_DECAY` + numeric decay duration / cycle count
  - Filter application validity: `FILTER_INVALID_BAND`, `FILTER_DESIGN_FAILED` (D19/D20)

Nice-to-have diagnostics (later):

- Instantaneous frequency drift metrics (`INSTANT_FREQ_DRIFT`)
- Filter ringing risk metrics beyond hard failures (`FILTER_RINGING_RISK`)
- Sensitivity of `ζ` to parameter perturbations (`FILTER_SENSITIVITY_HIGH`)
- Higher-order multi-modal indicators / clustering statistics across hits (beyond the core global peak list)

### F33) Define “SNR estimate” precisely

- Time-domain SNR (impact vs noise window)
- Frequency-domain SNR (peak vs noise floor band)
- Both?

✅ Decision:

- Use **both** a time-domain SNR (per hit) and a frequency-domain SNR (per peak), because they answer different field questions:
  - Time-domain SNR: "is this hit recording usable at all?" (on-site go/no-go)
  - Frequency-domain SNR: "is this PSD peak a real mode candidate?" (peak validity; see E26/E27)

Frequency-domain SNR (per peak, required):

- Definition (from E27):
  - `peak_snr_db = 10 * log10(peak_power / noise_floor)`
  - `noise_floor` is computed from the PSD band via E26.

Time-domain SNR (per hit, required):

- Definition:
  - `snr_td_db = 20 * log10(rms(signal_window) / rms(noise_window))`
  - Use RMS (or standard deviation) computed on the response signal after DC removal.
- Default windows (v1):
  - `signal_window`: the early portion of the analyzed ringdown (after `settle_s`), e.g. the first 20% of the ringdown window.
  - `noise_window`: the tail portion of the ringdown, e.g. the last 20% of the ringdown window (or the last `noise_tail_s`, whichever is shorter).
- If the noise window is too short or near-zero, the metric MUST be reported as not-computed (do not invent a value).

Hammer-channel detection quality metric (related, not named SNR):

- For hit detection on the hammer channel, report a robust detection-strength metric such as:
  - `hit_strength_sigma = (peak_height - baseline_median) / robust_sigma_mad`
  - and/or peak prominence.
- This is used for on-site sanity checking of hit detection, but is distinct from response SNR.

Reproducibility:

- Outputs MUST log the exact windowing rules and fractions used for `snr_td_db` and the values of `settle_s` / `ring_s` / `noise_tail_s` that affect them.

### F34) Beating detection

- What metric is used (envelope modulation depth, spectral splitting, Hilbert envelope peaks)?
- What threshold triggers BEATING_DETECTED?

✅ Decision:

Current implementation note:

- Present code does not explicitly detect beating; it only indirectly rejects some cases via poor envelope fit quality (low R²) or non-physical `ζ` (negative).

Beating detection (v1 core):

- Beating is detected primarily in the time domain on the response signal after per-peak band-pass filtering around `fi`.
- Metric: envelope modulation score computed from the analytic envelope.
  - Compute band-limited signal `y_filt(t)` around `fi`.
  - Compute envelope `e(t) = abs(hilbert(y_filt(t)))`.
  - Over the candidate decay-fit window (or the full analyzed ringdown after `transient_s`), compute a smoothed trend `e_trend(t)` using a moving median/mean with a window long compared to `1/fi`.
  - Define relative modulation `m(t) = (e(t) - e_trend(t)) / max(e_trend(t), eps)`.
  - Define `beating_score = rms(m(t))`.
- Threshold:
  - Trigger `BEATING_DETECTED` when `beating_score >= beating_score_max`.
  - Default: `beating_score_max = 0.20` (dimensionless; configurable).

Reporting / reproducibility:

- Always report `beating_score` (when computable) alongside the `BEATING_DETECTED` flag.
- Log the smoothing window length used for `e_trend(t)` and the exact time window used for computing `beating_score`.

### F35) Envelope monotonicity

- What test is used (smoothed monotonicity, % of increasing steps, slope sign stability)?

✅ Decision:

Current implementation note:

- Present code does not explicitly test envelope monotonicity; it relies mainly on envelope fit quality (R²) and sign/validity of the fitted decay slope.

Envelope monotonicity diagnostic (v1 core):

- Goal: detect when the (band-limited) amplitude envelope is not consistently decaying (often due to coupling/beating, reflections, or noise domination).
- Signal: compute the analytic envelope `e(t) = abs(hilbert(y_filt(t)))` on the per-peak band-passed response.
- Compute a smoothed trend envelope `e_trend(t)` (same smoothing approach as in F34).
- Define a monotonicity metric on the analysis window (after `transient_s`):
  - Let `d = diff(log(max(e_trend, eps)))`.
  - Define `increase_frac = count(d > 0) / len(d)`.
  - Define `monotonicity_score = 1 - increase_frac` (1.0 = perfectly non-increasing).
- Threshold / flag:
  - Trigger `ENVELOPE_NON_MONOTONIC` when `increase_frac >= envelope_increase_frac_max`.
  - Default: `envelope_increase_frac_max = 0.10` (configurable).

Reporting / reproducibility:

- Always report `increase_frac` (and/or `monotonicity_score`) alongside the `ENVELOPE_NON_MONOTONIC` flag.
- Log the smoothing window and exact time window used for the computation.

### F36) Instantaneous frequency stability

- How is it computed (Hilbert phase derivative, zero-crossing)?
- What drift threshold triggers INSTANT_FREQ_DRIFT?

✅ Decision:

Current implementation note:

- Present code does not compute instantaneous frequency stability.

Instantaneous frequency stability diagnostic (v1 core):

- Compute instantaneous frequency on the per-peak band-passed response `y_filt(t)`.
- Default method: analytic signal phase derivative (Hilbert-based).
  - `z(t) = hilbert(y_filt(t))`
  - `phi(t) = unwrap(angle(z(t)))`
  - `f_inst(t) = (fs / (2*pi)) * diff(phi(t))`
- Over the analysis window (after `transient_s`, and preferably over the same window used for damping fit):
  - `f_med = median(f_inst)`
  - `f_std = robust_sigma_mad(f_inst)` (or standard deviation with outlier trimming; method must be logged)
  - `inst_freq_rel_jitter = f_std / max(f_med, eps)`
- Threshold / flag:
  - Trigger `INSTANT_FREQ_DRIFT` when `inst_freq_rel_jitter >= inst_freq_rel_jitter_max`.
  - Default: `inst_freq_rel_jitter_max = 0.05` (5%; configurable).

Reporting / reproducibility:

- Always report `f_med`, `f_std`, and `inst_freq_rel_jitter` (when computable) alongside the `INSTANT_FREQ_DRIFT` flag.
- Log the exact time window used and any outlier handling used in the computation.

### F37) Filter dominance / ringing risk

- What metric distinguishes filter ringing from true decay?

✅ Decision:

Current implementation note:

- Present code does not explicitly detect filter dominance / ringing risk; it relies on conservative defaults and transient skipping (`transient_s`).

Filter dominance / ringing risk diagnostics (v1 core + optional refinement):

- Goal: detect when a band-pass filter may be driving the observed decay/envelope behavior (high-Q / narrow band), making damping estimates unreliable.

Core metric (required; deterministic; cheap):

- Compute a bandwidth / Q-like indicator from the applied band-pass:
  - `bw_hz = hi_hz - lo_hz`
  - `q_factor = fi / max(bw_hz, eps)`
- Threshold / flag:
  - Trigger `FILTER_RINGING_RISK` when `q_factor >= q_factor_max`.
  - Default: `q_factor_max = 5.0` (configurable).

Optional refinement (allowed; not required for v1):

- Estimate the filter's effective ringing duration by applying the exact filtering pipeline to a delta (impulse) input:
  - Generate an impulse `delta[n]` of sufficient length.
  - Apply the same band-pass and zero-phase filtering (`filtfilt`) as used for the response.
  - Compute envelope of the impulse response and measure `ringing_tail_s`: time to drop below a specified level (e.g. -40 dB from peak).
- Threshold / flag:
  - Trigger `FILTER_RINGING_RISK` when `ringing_tail_s` is a significant fraction of the fit window (configurable).
  - Default: `ringing_tail_db = -40 dB`, `ringing_ratio_max = 0.25`.

Reporting / reproducibility:

- Always report `bw_hz` and `q_factor` alongside the `FILTER_RINGING_RISK` flag.
- If impulse-response refinement is used, report `ringing_tail_s` alongside the flag.
- Outputs MUST log the thresholds used (`q_factor_max`, and any impulse-response settings) and the applied band-pass bounds (`lo_hz`, `hi_hz`).

### F38) Sensitivity of ζ to small parameter changes

- Which parameters are perturbed (filter bandwidth, fit range, start time)?
- What sensitivity threshold triggers FILTER_SENSITIVITY_HIGH?

✅ Decision:

Current implementation note:

- Present code does not compute sensitivity of `ζ` to parameter perturbations.

Scope decision:

- Sensitivity analysis is **nice-to-have** and is not required for v1.
- Rationale: the field-first priority is on on-site acquisition quality and clear coupled-mode flags; sensitivity sweeps add compute and complexity and are better introduced after the core pipeline is validated.

Future intent (when implemented):

- Perturb a small set of parameters around their configured values and measure the relative change in `ζ`:
  - filter bandwidth multipliers (e.g. +/- 10%)
  - fit start offset (e.g. `transient_s` +/- 50 ms)
  - fit end cap (e.g. `fit_max_s` +/- 10%)
- Define a normalized sensitivity metric, e.g. `zeta_sensitivity = max(|Δζ|) / max(|ζ|, eps)`.
- Trigger `FILTER_SENSITIVITY_HIGH` when `zeta_sensitivity >= zeta_sensitivity_max` (configurable).

---

## G) Damping estimators (exact procedure + applicability)

⏳ Not discussed yet (G39–G46)

### G39) Time-domain log decrement

- Peaks-to-peaks?
- Envelope fit?
- Linear regression on log envelope?

✅ Decision:

Current implementation note:

- Present code uses an envelope-fit approach: compute analytic envelope (Hilbert) on a band-passed response and fit a line to `log(envelope)` via linear regression.

Rewrite plan note:

- Implement TD envelope fit as a dedicated estimator module with both full-window and established-decay variants.
- Enforce frequency-aware fit guards (`decay_min_duration_s`, `decay_min_cycles`) and attach reason codes on failure.

TD damping estimator (v1 baseline): envelope fit with linear regression on log-envelope.

- For each candidate peak frequency `fi`, compute a band-limited response `y_filt(t)` (per D19/D20).
- Compute the analytic amplitude envelope:
  - `e(t) = abs(hilbert(y_filt(t)))`
- Fit an exponential decay by linear regression in log space on the chosen fit window:
  - `log(e(t)) = c + m * t`
- Convert slope to damping ratio using the target frequency:
  - `zeta = -m / (2*pi*fi)`

Reporting / reproducibility:

- Report the fitted slope/intercept (`m`, `c`) and fit quality (e.g. `env_fit_r2`).
- Peaks-to-peaks log decrement is out of scope for v1 and may be added later as an additional estimator.

Energy decay as-built notes:

- Negative or non-finite energy-decay zeta values are treated as NOT_COMPUTED and flagged `BAD_ZETA_ENERGY` + `EFFECTIVE_DAMPING_ONLY`.

Diagnostics default thresholds (v1):

- `beating_score_max = 0.20`
- `envelope_increase_frac_max = 0.10`
- `inst_freq_rel_jitter_max = 0.05`
- `q_factor_max = 5.0`

### G40) Do you use the full window or only the established decay segment?

✅ Decision:

Current implementation note:

- Present code primarily attempts an "established" fit by skipping an initial transient and searching for a fit start that meets an R² threshold, while also limiting the fit tail to avoid the noise floor.

Fit policy (v1): hybrid (compute both; do not silently switch).

- For each hit and each candidate peak `fi`, the analysis SHOULD attempt to compute both:
  1) Full-window fit
     - Fit uses the standard ringdown analysis window (after `transient_s`), with an end chosen to avoid fitting deep into noise (e.g. via `fit_max_s` and/or a noise-floor stop rule).
  2) Established-decay fit
     - Fit start is selected (opportunistically) to find a sub-window that satisfies quality criteria (e.g. `env_fit_r2 >= established_r2_min`, and diagnostic checks such as monotonicity / beating as available).
     - Fit end follows the same noise-avoidance rule as the full-window fit.
- Both results MUST be preserved and reported when computable.
  - Failure to find an established segment is not an error; it yields NOT_COMPUTED (or WARNING/REJECTED) for that fit variant with an explicit reason.
- "Best guess" selection (if enabled) SHOULD prefer the established-decay fit when it is OK; otherwise fall back to the full-window fit only if it meets minimum acceptance criteria.

Reproducibility:

- Outputs MUST log fit start/end times (or indices) for both fit variants and all thresholds used for established-fit selection.

### G41) Define TOO_SHORT_DECAY

- Minimum number of cycles?
- Minimum number of peaks?

✅ Decision:

Current implementation note:

- Present code has only coarse length-based guards (e.g. minimum samples/seconds). This is not frequency-aware and is insufficient for low-frequency structures.

TOO_SHORT_DECAY definition (v1): frequency-aware minimum cycles + minimum duration.

- For each hit, each candidate peak frequency `fi`, and each fit variant (full-window and established-decay):
  - `fit_duration_s = t_fit_end - t_fit_start`
  - `n_cycles = fit_duration_s * fi`
- Trigger `TOO_SHORT_DECAY` when either condition is violated:
  - `fit_duration_s < decay_min_duration_s`
  - `n_cycles < decay_min_cycles`

Preset default proposals:

- Structures preset:
  - `decay_min_duration_s = 1.0`
  - `decay_min_cycles = 8`
- Xylophone preset:
  - `decay_min_duration_s = 0.10`
  - `decay_min_cycles = 20`

Reporting / reproducibility:

- Always report `fit_duration_s` and `n_cycles` alongside the `TOO_SHORT_DECAY` flag.
- Outputs MUST log the thresholds used and which fit variant they apply to.

### G42) Half-power bandwidth method

- Use −3 dB points from PSD peak?
- Is smoothing allowed?

✅ Decision:

Current implementation note:

- Present code does not implement a frequency-domain half-power bandwidth damping estimator.

Half-power bandwidth estimator (v1): allowed and computed when conditions permit.

- Method:
  - Work on the PSD of the response for the given hit (per E25).
  - For each candidate peak at frequency `fi` with peak power `P_peak`, find the left/right half-power points `f1 < fi < f2` such that the PSD drops by 3 dB from the peak.
  - Half-power level definition:
    - In linear power: `P_half = 0.5 * P_peak`.
    - (Equivalently in dB: `P_half_db = P_peak_db - 3.0103 dB`).
  - Damping ratio estimate:
    - `zeta_hp = (f2 - f1) / (2 * fi)`.

Applicability / failure rules:

- This estimator MUST be treated as a modal (single-peak) method and MUST be WARNING/REJECTED when the peak is not isolated.
- If a coupled/multi-peak region is detected (E29) or half-power crossings cannot be found cleanly on both sides, the estimate MUST be NOT_COMPUTED (or REJECTED) with a reason code such as `PSD_MULTI_PEAK` and/or `HALF_POWER_NOT_FOUND`.
- If the computed bandwidth is non-physical (`f2 <= f1`, `zeta_hp <= 0`, or `f1/f2` outside analysis band), the estimate MUST be rejected with an explicit reason code (e.g. `BAD_ZETA_HP`).

Smoothing policy:

- Smoothing of the PSD is allowed to stabilize half-power point detection, but must be conservative.
- Default (v1): no smoothing beyond the Welch averaging inherent in the PSD.
- If enabled, smoothing MUST be explicitly configured (type + window) and MUST be logged.

Reporting / reproducibility:

- Always report `f1`, `f2`, `bandwidth_hz = f2 - f1`, and `zeta_hp` alongside any flags.
- Outputs MUST log whether PSD smoothing was applied and all parameters used.

### G43) What if half-power points cannot be found cleanly (multi-peak region)?

✅ Decision:

Current implementation note:

- Present code does not implement the half-power estimator, so there is no current behavior.

Policy:

- If half-power points cannot be found cleanly on both sides of the peak, the half-power estimator MUST NOT return a numeric damping value as if it were valid.
- The estimate MUST be NOT_COMPUTED (preferred) or REJECTED with explicit reason codes.

Definition of "cannot be found cleanly" (v1):

- Either side (left or right) fails to cross the half-power level within the allowed search window, or
- The crossing is ambiguous due to multiple local maxima / shoulders in the search region, or
- The peak is marked as part of a coupled / multi-peak region (E29).

Defaults / search window:

- Search for half-power crossings only within the peak's isolated neighborhood (e.g. bounded by adjacent-peak midpoints when available, consistent with D20 guardrails).
- If optional PSD smoothing is enabled, it may be applied before searching crossings, but smoothing MUST NOT be used to "force" crossings in clearly multi-peak regions.

Reason codes (initial):

- `HALF_POWER_NOT_FOUND_LEFT`
- `HALF_POWER_NOT_FOUND_RIGHT`
- `HALF_POWER_AMBIGUOUS`
- `PSD_MULTI_PEAK`

Reporting:

- The report MUST state which side failed (left/right) and include the search window used.

### G44) Energy decay method

- What exact energy proxy is used (v², a²/ω², integral of squared signal)?

✅ Decision:

Current implementation note:

- Present code does not implement an Energy Decay damping estimator.

Energy decay estimator (v1): implement a small, purposeful set of proxies (not all).

- Rationale: Energy decay is primarily a robust fallback for coupled / multi-mode responses; returning many competing "effective damping" values is confusing and not necessary for v1.

Allowed proxies:

1) Primary (default): envelope-squared energy proxy
   - Compute band-passed response `y_filt(t)` around target `fi`.
   - Compute analytic envelope `e(t) = abs(hilbert(y_filt(t)))`.
   - Define energy proxy `E(t) = e(t)^2`.
   - Fit an exponential decay rate on `log(E(t))` over the chosen fit window.
2) Optional (not default): signal-squared proxy
   - `E(t) = y_filt(t)^2` and fit decay on a smoothed/log-transformed representation.

Deferred (out of scope for v1):

- Velocity-squared proxies requiring integration (`v(t)^2`) and related variants (`a^2/omega^2`).
  - If/when added, they must follow D22 drift-control requirements and be explicitly labeled as effective damping.

Reporting / reproducibility:

- Outputs MUST log the chosen `energy_proxy` and any smoothing applied before fitting.

### G45) How do you convert decay rate to ζ (assumed relationship)?

✅ Decision:

Current implementation note:

- Present code converts the slope of a log-envelope fit into `ζ` using `fi` as the target frequency.

Shared physical model (lightly damped SDOF approximation):

- For a single-mode ringdown, the envelope decays approximately as:
  - `e(t) = A * exp(-ζ * ω_n * t)` where `ω_n = 2*pi*fi`.

Conversion rules by estimator:

- TD envelope fit (G39):
  - Fit `log(e(t)) = c + m*t`.
  - Define `alpha = -m`.
  - Convert: `ζ = alpha / (2*pi*fi)`.

- Energy decay (G44):
  - If fitting on an energy proxy that decays as `E(t) ~ exp(-2*ζ*ω_n*t)` (e.g. `E=e^2` or a sufficiently smoothed `E=y^2`):
    - Fit `log(E(t)) = c_E + m_E*t`.
    - Define `alpha_E = -m_E`.
    - Convert: `ζ = alpha_E / (4*pi*fi)`.
  - The implementation MUST document which proxy is assumed to have the `exp(-2*ζ*ω_n*t)` form and MUST log it (`energy_proxy`).

- Half-power bandwidth (G42):
  - `ζ_hp = (f2 - f1) / (2*fi)`.

Reporting / reproducibility:

- Outputs MUST log the fitted slope(s) (`m`, `m_E` where applicable), the derived decay rate(s) (`alpha`, `alpha_E`), and the exact `fi` used.

### G46) When do you automatically label EFFECTIVE_DAMPING_ONLY?

✅ Decision:

Current implementation note:

- Present code does not have structured reason codes; it uses a small set of reject reasons and does not distinguish modal vs effective damping.

Labeling policy:

- Any estimate produced by the Energy Decay method (G44) MUST include the reason code `EFFECTIVE_DAMPING_ONLY`.
  - Rationale: even for clean signals, the energy-decay rate represents an effective decay of an energy proxy and is not guaranteed to equal true modal damping in the presence of multiple participating modes.

Status interaction (field-friendly):

- If coupling/multi-mode indicators are present for the peak/hit (e.g. `PSD_MULTI_PEAK`, `MULTI_MODE_SUSPECTED`, `BEATING_DETECTED`), Energy estimates SHOULD be downgraded to at least WARNING, while still reporting the numeric value.
- If the signal otherwise appears single-mode and diagnostics are clean, the Energy estimate MAY be marked OK but must still carry `EFFECTIVE_DAMPING_ONLY`.

Reporting / reproducibility:

- Reports MUST explain the meaning of `EFFECTIVE_DAMPING_ONLY` in plain language and MUST not present Energy-based `ζ` as a pure modal property.

---

## H) Status classification rules (OK / WARNING / REJECTED)

⏳ Not discussed yet (H47–H51)

### H47) Do you want a deterministic mapping: diagnostic thresholds → status?

✅ Decision:

Current implementation note:

- Present code uses a small set of ad-hoc reject reasons and does not implement a structured `OK/WARNING/REJECTED` status framework.

Status mapping policy:

- Yes: the mapping from diagnostics/reason-codes to final estimate status MUST be deterministic and reproducible.
- The software MUST implement an explicit, documented rule set that converts computed diagnostics (numeric metrics + flags) into:
  - `OK`, `WARNING`, `REJECTED`, and (see H50) `NOT_COMPUTED`.
- Thresholds used for status decisions MUST be configurable (advanced settings) and MUST be logged in outputs.
- The mapping MUST be transparent:
  - An estimate's status MUST be explainable as the result of its triggered reason codes.
  - No single hidden "quality score" may override the documented rules.

### H48) Are some reason codes always REJECTED (hard failures), while others are WARNING (soft failures)?

✅ Decision:

Current implementation note:

- Present code has only a small set of reject reasons and does not distinguish hard failures vs soft warnings.

Policy:

- Yes: reason codes are partitioned into at least two severity classes:
  - Hard failures (force `REJECTED` or `NOT_COMPUTED` for the affected estimator)
  - Soft failures (force at least `WARNING`, but may still allow a numeric value to be reported)

Hard failures (v1 baseline):

- `FILTER_INVALID_BAND`, `FILTER_DESIGN_FAILED` (filter cannot be applied as specified)
- `TOO_SHORT_DECAY` (insufficient decay data for a meaningful fit)
- Half-power specific:
  - `HALF_POWER_NOT_FOUND_LEFT`, `HALF_POWER_NOT_FOUND_RIGHT`, `HALF_POWER_AMBIGUOUS`
  - `BAD_ZETA_HP`
- Peak selection specific:
  - `NO_VALID_PEAKS` (no candidate peaks pass validity checks)

Soft failures (v1 baseline):

- `SNR_LOW` (may still compute but status cannot be OK)
- `PSD_MULTI_PEAK`, `MULTI_MODE_SUSPECTED` (coupling suspected)
- `BEATING_DETECTED`
- `ENVELOPE_NON_MONOTONIC`
- `INSTANT_FREQ_DRIFT`
- `FILTER_RINGING_RISK`

Notes / method-specific nuance:

- Some reason codes are hard failures only for certain estimators:
  - In a coupled/multi-peak region (`PSD_MULTI_PEAK`), modal damping estimators (TD/FD) are typically WARNING/REJECTED, while frequency reporting can remain OK.
  - Half-power bandwidth is not applicable in multi-peak regions and should become `NOT_COMPUTED` (hard failure) there.
- `EFFECTIVE_DAMPING_ONLY` is not a failure; it is a labeling constraint that must accompany Energy estimates.

Reproducibility:

- The hard/soft mapping MUST be documented and MUST be logged (versioned) so status changes are auditable.

### H49) Can multiple reason codes coexist, and is there a priority ordering?

✅ Decision:

- Multiple reason codes MAY coexist on the same estimate.
  - The tool MUST preserve and report the full set of applicable reason codes (do not collapse to a single reason).
- Priority ordering:
  - No explicit priority ordering is required for v1.
  - Status is determined by the deterministic mapping rules (H47/H48): any hard-failure reason code forces `REJECTED`/`NOT_COMPUTED`, otherwise any soft-failure reason code forces at least `WARNING`, otherwise `OK`.
- Reporting:
  - Reports MUST show all reason codes attached to each estimate.

### H50) Do you want a NOT_COMPUTED status for methods that aren’t mathematically possible, distinct from REJECTED?

✅ Decision:

- Yes: introduce a distinct `NOT_COMPUTED` status for estimators that cannot be computed due to missing prerequisites or mathematical impossibility.
- Meaning:
  - `NOT_COMPUTED`: the method was not applicable or could not be executed (e.g. insufficient data, missing half-power crossings, invalid filter band).
  - `REJECTED`: the method produced a numeric value but diagnostics indicate it is not physically meaningful / must not be used.
- Reporting:
  - `NOT_COMPUTED` entries MUST still appear in tables with their method name, status, and reason codes.
  - Numeric value fields SHOULD be blank or `NaN` (do not invent values).

### H51) Should REJECTED values still show numeric ζ, and should they be excluded from plots/averages by default?

✅ Decision:

- Yes: rejected estimates MAY still show a numeric value for transparency and engineering judgment.
  - The value MUST be presented alongside its status (`REJECTED`) and reason codes; it must never appear as an unqualified "result".
- Aggregation / plotting defaults:
  - REJECTED estimates MUST be excluded from summary statistics (means/medians) by default.
  - REJECTED estimates SHOULD be excluded from default plots/trendlines, but MAY be shown as faint/annotated points if helpful.
- Reporting:
  - Reports MUST clearly communicate that REJECTED values have no physical meaning under the method's assumptions and must not be used for decisions.

---

## I) “Best guess” policy

⏳ Not discussed yet (I52–I55)

### I52) If multiple OK estimates exist (TD_raw, TD_filt, FD, Energy), which wins?

✅ Decision:

Current implementation note:

- Present code produces a single TD envelope-fit estimate (band-passed) and does not implement multiple estimators or a "best guess" selector.

Best-guess selection order (v1): deterministic method preference with status gating.

- Best guess is selected per (hit, candidate peak `fi`) (see I53).
- Only consider estimates with status `OK` first.
- If one or more `OK` estimates exist for the same (hit, `fi`), choose the first available in this preference order:
  1) TD envelope fit on filtered response (`TD_FILT`)
  2) FD half-power bandwidth (`FD_HALF_POWER`)
  3) TD envelope fit on raw response (`TD_RAW`) (if implemented)
- If no `OK` estimates exist but one or more `WARNING` estimates exist, repeat the same preference order among `WARNING`.
- If neither `OK` nor `WARNING` exist, no best guess is reported.

Notes:

- Energy-based estimates are handled separately (see I54) because they are labeled `EFFECTIVE_DAMPING_ONLY`.

### I53) Is “best guess” per peak fi or per hit overall?

✅ Decision:

- Best guess is computed per **peak `fi` per hit**.
  - Rationale: in coupled / multi-peak responses, a hit may legitimately contain multiple candidate modes; forcing a single best guess per hit would hide that reality.
- Reporting:
  - Each hit section SHOULD list candidates and show a best guess (if any) per candidate peak.
  - A separate overall per-hit convenience summary MAY be included, but it must not suppress additional peaks.

### I54) Should best guess ever come from the Energy method, or only if no modal method is OK?

✅ Decision:

- Default rule (v1): Energy method is used for best guess **only as a fallback**.
  - If any modal estimator (TD/FD) is `OK` for the same (hit, `fi`), the best guess MUST come from a modal estimator (see I52).
  - If no modal estimator is `OK` or `WARNING`, but an Energy estimate exists, the Energy estimate MAY be used as the best guess and MUST be labeled `EFFECTIVE_DAMPING_ONLY`.
- Reporting:
  - When Energy is selected as best guess, the report MUST explicitly state that it is effective damping (not pure modal damping) and show the reason codes that led to modal methods being unavailable.

### I55) Should best guess prefer

- Consistency across methods
- Consistency across hits
- Lowest sensitivity score?

✅ Decision:

v1 tie-break policy: prioritize per-hit, per-peak estimate quality (not cross-hit optimization).

- Rationale: v1 is field-focused; cross-hit optimization is valuable but adds complexity and can hide per-hit issues.
- Within the method preference order (I52), if multiple candidate estimates remain (e.g. multiple fit variants), choose the one with the best quality metrics, in this order:
  1) Highest status (OK > WARNING)
  2) Highest envelope fit R² (for TD/Energy methods)
  3) Lowest `beating_score`
  4) Lowest `increase_frac` (envelope non-monotonicity)
  5) Highest `peak_snr_db`
- If still tied, choose the estimate with the longest valid fit window (largest `n_cycles`).

Deferred (nice-to-have later):

- Cross-hit consistency scoring and sensitivity-based selection.

---

## J) Aggregation across hits

⏳ Not discussed yet (J56–J60)

### J56) How do you group peaks across hits (frequency clustering method)?

✅ Decision:

Current implementation note:

- Present code does not perform true cross-hit mode grouping: it produces one `fn` per hit and then reports simple summary statistics across accepted hits.

Cross-hit grouping (v1): deterministic frequency clustering using the global peak list.

- Use the global (across-hits) candidate peak list from E24 as the primary set of "mode groups".
- For each hit, match each per-hit candidate peak to the nearest global peak frequency within the tolerance defined in J57.
- If a per-hit peak cannot be matched to any global peak, it MAY be reported as a hit-local mode group (explicitly labeled as hit-local / non-repeatable).
- Each mode group MUST have a stable identifier (e.g. `mode_id = M01, M02, ...`) used consistently in CSV/JSON/reporting.
- Reproducibility:
  - Outputs MUST log the grouping inputs (global peak list) and the final assignments (per-hit peak -> mode_id).

### J57) What tolerance defines “same mode” across hits (Hz or %)?

✅ Decision:

- Use a hybrid tolerance that scales with frequency:
  - `mode_match_tol_hz(fi) = max(mode_match_tol_abs_hz, mode_match_tol_frac * fi)`.
- Default proposals:
  - Structures preset: `mode_match_tol_abs_hz = 0.5`, `mode_match_tol_frac = 0.03`
  - Xylophone preset: `mode_match_tol_abs_hz = 5.0`, `mode_match_tol_frac = 0.01`
- These tolerances MUST be configurable and MUST be logged.

### J58) What summary statistics do you want?

- Mean / median
- Trimmed mean
- Min / max
- Confidence interval?

✅ Decision:

Summary statistics (v1): field-friendly, robust, and transparent.

- For each mode group (and per estimator/method where applicable), report at minimum:
  - `n_total` (hits considered), `n_ok`, `n_warning`, `n_rejected`, `n_not_computed`
  - central tendency: median and mean
  - spread: min/max and a robust spread metric (IQR or MAD)
- Confidence intervals are not required for v1.
- Aggregation rules:
  - REJECTED values are excluded by default (H51).
  - NOT_COMPUTED values are counted but not included in numeric aggregates.
- Reporting MUST clearly state which statuses are included in each aggregate.

### J59) Do you want separate aggregates for OK-only vs (OK + WARNING)?

✅ Decision:

- Yes: provide both aggregates by default.
  - OK-only aggregate (highest confidence)
  - OK+WARNING aggregate (broader context)
- REJECTED values are excluded from both; NOT_COMPUTED are counted only.
- Reports MUST present both aggregates side-by-side (or clearly labeled) to preserve engineering judgment.

### J60) If some hits have different dominant peaks, do you

- Keep separate mode groups
- Select one “global mode 0”
- Report “multiple mode candidates” only?

✅ Decision:

- Keep separate mode groups.
  - The tool must not force a single global mode ("mode 0") in v1.
  - Rationale: coupled/multi-mode behavior is a first-class diagnostic; collapsing it would hide important field information.
- Reporting MAY highlight a "primary" mode group for convenience (e.g. highest `n_ok` or highest median `peak_snr_db`), but must still list all mode groups.

---

## K) Reporting: required content and structure

⏳ Not discussed yet (K61–K65)

### K61) Pre-process report: should it include hit count and hit timestamps?

✅ Decision:

Current implementation note:

- Present preprocess report is minimal (WAV specs + overview plot). It does not yet emphasize field go/no-go metrics.

Preprocess report (v1): yes, include hit count + timestamps and field quality checks.

- Outputs:
  - `report_preprocess.md` and `report_preprocess.pdf` are required by default.
- The preprocess report MUST include:
  - WAV file specs (path, fs, samples, duration)
  - Channel role mapping (hammer/response) + autodetect confidence if autodetect was used
  - Hit detection summary:
    - `n_hits_found`, `n_hits_used`
    - hit timestamps list (seconds) or a small table (hit_id, t_hit)
    - detection threshold and key detector settings
  - On-site go/no-go signal quality diagnostics (field-first):
    - clipping metrics (per channel) + `CLIPPED_SIGNAL` flag
    - overall response SNR-like metric per hit (`snr_td_db`) + `SNR_LOW` flag
  - Global overview plot (hammer + response aligned, with hit markers)


### K62) Per-hit report structure

- One markdown per hit
- One combined markdown with sections?

✅ Decision:

- v1 output is a single combined modal report:
  - `modal_report.md` and `modal_report.pdf`.
- The modal report MUST include per-hit sections (e.g. `H001`, `H002`, ...).
- Optional (not required for v1): emit separate per-hit markdown files in addition to the combined report.


### K63) Should each hit section include

- Raw hammer + response window plots?
- Filtered response plot per candidate peak?
- PSD plot with annotated peaks?
- Decay/envelope plot per method?

✅ Decision:

Yes. For v1, each hit section MUST include per-hit and per-peak artifacts sufficient for engineering judgment.

- Per-hit required content:
  - Raw windowed response plot (time) with the analyzed ringdown window highlighted
  - PSD/Welch plot with:
    - analysis band bounds
    - detected candidate peaks annotated
    - noise floor indication (E26)
  - A compact table summarizing, for each candidate peak `fi` (cap at `max_candidate_peaks = 5`):
    - `fi` (bin and refined), `peak_snr_db`, coupled-region flags, and best-guess `ζ` (if any)

- Per-(hit, fi) required content (up to 5 peaks per hit):
  - Filtered response plot around `fi`
  - Envelope/decay plot(s) showing:
    - the envelope (or energy proxy)
    - the fitted line/fit window
    - numeric diagnostics + status/reason codes alongside the estimate
  - If half-power bandwidth was computed, annotate `f1`/`f2` on the PSD zoom for that peak.


### K64) Do you want machine-readable outputs (JSON / CSV) for database ingestion?

✅ Decision:

- Yes: machine-readable outputs are required.
- v1 required outputs:
  - CSV "long" table with one row per (hit, peak `fi`, estimator method).
  - CSV "best guess" table with one row per (hit, peak `fi`) capturing best guess `fn` and `ζ` plus status/reasons.
- Optional (allowed, not required for v1): JSON export of the full structured results (recommended for future database integration).


### K65) What is the directory structure contract (filenames, paths) that must not change?

✅ Decision:

- The output directory structure is part of the public contract and must remain stable across versions (v1).

Required structure (v1):

```
out_dir/
  report_preprocess.md
  report_preprocess.pdf
  modal_report.md
  modal_report.pdf
  modal_results_long.csv
  modal_results_best_guess.csv
  figures/
    overview_two_channels.png
    hits/
      H001_response.png
      H001_psd.png
      H001_F01_filtered.png
      H001_F01_decay.png
      ...
```

Notes:

- `F01..F05` correspond to candidate peaks for that hit (ranked by validity/strength; max 5).
- If a file is not generated (e.g. estimate NOT_COMPUTED), the report should still include a placeholder row; images may be omitted.

---

## L) Output determinism and reproducibility

⏳ Not discussed yet (L66–L68)

### L66) Which parameters are considered part of the “analysis config” and must be echoed in reports?

✅ Decision:

Current implementation note:

- Present reports include limited configuration context (some values are implied, and the persisted UI config is not fully echoed into outputs).

Analysis config contract (v1): echo everything that can change results.

- The reports and machine-readable outputs MUST include an "analysis config" section/object containing all parameters that affect detection, windowing, spectral estimation, peak selection, filtering, damping estimation, diagnostics, and reporting.
- At minimum this includes:
  - Input WAV metadata: path/name, fs, duration, channel roles (hammer/response), autodetect method + scores (if used)
  - Hit detection parameters: baseline_s, threshold_sigma, min_separation_s, polarity, smoothing/highpass settings (and any other detection knobs)
  - Windowing parameters: pre_s, post_s, settle_s, ring_s
  - PSD parameters: method=welch, window, nperseg policy (`psd_df_target_hz`, min/max), overlap, detrend, scaling
  - Noise floor parameters: percentile q
  - Peak selection parameters: min_peak_snr_db, max_candidate_peaks, peak merging spacing (E28)
  - Filter parameters: family, order, zero_phase, band selection multipliers (0.6/1.4), guardrail behavior
  - Fit parameters: transient_s, established_min_s, established_r2_min, fit_max_s, noise_tail_s, noise_mult
  - Diagnostic thresholds: beating_score_max, envelope_increase_frac_max, inst_freq_rel_jitter_max, q_factor_max, and any others used
  - Aggregation/grouping parameters: mode match tolerances (J57) and aggregation inclusion rules
- The config MUST be logged in a machine-readable way:
  - Include as a JSON block embedded in `modal_results_best_guess.csv` (e.g. a separate sidecar `analysis_config.json` is also acceptable).
  - Include a human-readable summary in both `report_preprocess.*` and `modal_report.*`.


### L67) Do you want a version stamp (package version / git hash) inside reports?

✅ Decision:

Current implementation note:

- Present outputs do not reliably stamp the software version or git revision.

Version stamping (v1): yes.

- All reports and machine-readable outputs MUST include:
  - package version (e.g. `wav-to-freq` version)
  - build identifier (git commit hash when available; otherwise "unknown")
  - timestamp of analysis run
- The goal is reproducibility and auditability of field results.


### L68) Should random or heuristic behavior be eliminated entirely?

✅ Decision:

Determinism policy (v1): yes, outputs must be deterministic for a given input + config.

- No random components are permitted in the analysis pipeline.
- Heuristics are allowed (e.g. "choose fit start that meets R² threshold"), but they MUST be deterministic and fully specified by the logged config.
- If any library behavior could introduce nondeterminism (e.g. multithreading), the implementation SHOULD avoid it or document it; results should be stable run-to-run.

---

## M) Limits and constraints

⏳ Not discussed yet (M69–M71)

### M69) Expected frequency ranges (e.g., 0–30 Hz structures vs 100–1000 Hz bench parts), and should defaults adapt?

✅ Decision:

Current implementation note:

- Present app already uses presets (e.g. Structures vs Xylophone) to set coherent default ranges and analysis knobs.

Frequency range policy (v1): presets + explicit user control.

- The tool MUST support at least two presets with clearly different expected ranges:
  - Structures (low-frequency)
  - Xylophone / small parts (higher-frequency)
- Defaults SHOULD adapt via preset selection (not via silent auto-detection).
- User MUST be able to explicitly set/override:
  - `fmin_hz`, `fmax_hz`
  - key time window parameters that interact with frequency resolution (`ring_s`, `post_s`, and PSD `psd_df_target_hz`).
- Reporting MUST show the selected preset name and the final effective `fmin_hz`/`fmax_hz` used.

### M70) What is the maximum WAV duration you expect (performance constraints)?

✅ Decision:

Current implementation note:

- Present tool operates on short field recordings (typically < 1 minute) and processes full arrays in memory.

Performance assumptions (v1): short files; warn on long inputs.

- Expected typical WAV duration: <= 60 s.
- Supported (v1): up to 5 minutes, assuming sufficient RAM, with performance possibly degraded.
- If duration exceeds a configurable threshold (default 2 minutes), the tool MUST:
  - warn prominently in the preprocess report (and UI if possible), and
  - still attempt to analyze unless the user aborts.
- Streaming / chunked processing is out of scope for v1.

### M71) Should the software handle clipped signals gracefully (analyze anyway with flags) or stop?

✅ Decision:

Current implementation note:

- Present code does not explicitly detect clipping as a first-class diagnostic; it may fail indirectly or produce biased estimates.

Clipping policy (v1): analyze by default, flag aggressively, and downgrade affected estimates.

- The tool MUST detect clipping per channel and report a numeric clipping metric.
- Default behavior is to continue analysis and attach `CLIPPED_SIGNAL` (soft failure) rather than stop.
- If clipping severity exceeds a configurable hard threshold (e.g. large fraction of samples at/near full scale), the tool MAY:
  - mark the affected hit(s) / channel(s) as not suitable for quantitative damping (e.g. force WARNING/REJECTED on damping estimates), and/or
  - mark hit detection results as unreliable.
- Reports MUST clearly communicate that clipped signals can invalidate damping estimates.

---

## N) Future-proofing (explicitly out of scope but named)

⏳ Not discussed yet (N72–N74)

### N72) Manual hit editing UI (add/remove hit): planned or not?

✅ Decision:

- Manual hit editing is explicitly out of scope for v1.
- Future intent: possible later enhancement (post-v1) if field workflow demands it.
- v1 mitigation: users may re-record, or externally crop/clean a WAV before analysis.

### N73) Multi-accelerometer / multi-channel files: planned or never?

✅ Decision:

- Multi-channel (more than 2 channels) support is out of scope for v1.
- v1 input contract remains: exactly 2 channels (hammer + response).
- Future intent: possible later, but only with an explicit configuration/UI to assign roles per channel.

### N74) Database integration: should a minimal JSON schema be specified now for future use?

✅ Decision:

- Yes: specify a minimal JSON schema for v1 to enable future database integration.
- v1 requirement: emit (or be able to emit) a single `analysis_results.json` capturing:
  - run metadata (timestamp, version/git hash)
  - input metadata (wav path, fs, duration, channel roles)
  - analysis config (per L66)
  - hit list (hit_id, t_hit, window bounds)
  - per-hit candidate peaks (rank, fi_bin, fi_refined, peak_snr_db, flags)
  - per (hit, fi) estimator results (method, value, status, reason_codes, diagnostics)
  - per-mode aggregation outputs (mode_id, summary stats)
- JSON schema may be informal (documented by example) in v1, but field names and structure must be stable.
