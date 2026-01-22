# specs.md (v1) - WAV Impact Modal Analysis Spec

This document is the normative v1 specification for `wav-to-freq`.

Decision log / rationale lives in `docs/specs_clarifications.md` (referenced throughout by ID).

Conventions:

- Requirement IDs use the same scheme as `docs/specs_clarifications.md` (A1, E26, K65, ...).
- Normative keywords: MUST, SHOULD, MAY.

---

## 1) Purpose

Analyze 2-channel WAV impact-hammer tests (hammer + response) to extract:

- candidate natural frequencies `fi` per hit
- damping estimates `zeta` per (hit, `fi`, method)
- diagnostics + reason codes that explain applicability/quality

The tool MUST "show the thing" (multi-peak / coupled behavior) instead of forcing a single number.

---

## 2) Inputs and configuration

Source: `docs/specs_clarifications.md` A1-A4.

- A1 (MUST): Input is stereo WAV only (2 channels required).
- A2 (MUST): User assigns channel roles (hammer vs response) in the TUI.
- A3 (MUST): App refuses to run unless channel roles are explicitly assigned.
- A4 (MUST): Channel mapping is persisted/logged in outputs (channel index + semantic role).

---

## 3) Hit detection contract

Source: `docs/specs_clarifications.md` B5-B10.

- B5 (MUST): Hit detection uses the hammer channel only.
- B6 (SHOULD): Hits are peaks in a processed hammer signal above a robust threshold, with prominence and distance constraints (formalize from implementation).
- B7 (MUST): Minimum separation between hits defaults to 0.30 s and is user-configurable.
- B8 (MUST): Hit detection is automatic in v1.
- B9 (MUST): Double taps/bounce handling is out-of-scope for v1; the tool focuses on diagnosis (preprocess report).
- B10 (MUST): No requirement to infer "missed" or "false positive" hits beyond reporting what was found.

---

## 4) Per-hit windows

Source: `docs/specs_clarifications.md` C11-C16.

- C11 (MUST): Hit window is anchored with pre-trigger only.
- C13/C14 (MUST): Post-hit duration is fixed seconds, default 1.5 s, configurable.
- C15 (MUST): If decay does not finish inside the window, compute anyway with diagnostics/flags.
- C16 (MUST): Hybrid approach: compute both full-window analysis and established-decay analysis when possible; log crop start/end.

---

## 5) Preprocessing and filtering

Source: `docs/specs_clarifications.md` D17-D23.

- D17 (MUST): Response DC offset is removed; no global response high-pass by default; any response filtering is method-specific and logged.
- D18 (MUST): No resampling; WAV sample rate is treated as final.

### 5.1) Per-peak band-pass

- D19 (MUST): Band-pass for per-peak isolation uses IIR Butterworth order 4 with zero-phase filtering (e.g. `filtfilt`).
- D20 (MUST): Default cutoff proposal is proportional to `fi`: `lo0 = 0.60*fi`, `hi0 = 1.40*fi` with clamps to `[fmin_hz, fmax_hz]` and digital limits; apply adjacent-peak guardrails when candidate peaks exist.
- D21 (MUST): No explicit padding/tapering by default; handle transients via a configurable `transient_s` fit skip; log it.

### 5.2) Hammer filtering

- D23 (MUST): Hammer channel may be processed for hit detection only; never for modal estimation. Raw hammer must be shown in preprocess reporting.

### 5.3) Energy-method integration policy

- D22 (MUST): Avoid fragile velocity integration in v1; if integration is used, it must be time-domain with drift control and fully logged.

---

## 6) Frequency estimation and peak handling

Source: `docs/specs_clarifications.md` E24-E30.

### 6.1) PSD

- E24 (MUST): Use both per-hit PSDs and a robust across-hits PSD (mean/median) to form a global candidate peak list.
- E24a (SHOULD): Global peak selection SHOULD include a low-frequency pass that is merged into the main list before de-duplication, to avoid suppressing low-frequency structural modes. Default low band: 1–100 Hz with a lower SNR gate (3 dB); settings are configurable and logged.
- E24b (SHOULD): Global peak selection SHOULD optionally include a hit-local union pass, retaining peaks that appear in at least `min_hits` hits (default 2) even if they are weak in the median PSD. Default hit-local SNR gate is 3 dB; thresholds and caps are configurable and logged.
- E24c (SHOULD): Global peak outputs SHOULD include a `peak_detection_count` for each peak when hit-local aggregation is enabled, indicating how many hits contributed to that peak group. A derived `detection_ratio` (count / total hits) MAY be included for reporting.
- E25 (MUST): Welch PSD is the reference; parameters are configurable but have logged defaults; `psd_df_target_hz` is the primary knob driving `nperseg` deterministically.
- E26 (MUST): Noise floor is percentile-based within the analysis band: `noise_floor = percentile(Pxx_band, q)` with default `q=60` (configurable; logged).

### 6.2) Peak validity

- E27 (MUST): Peak validity is SNR-based:
  - `peak_snr_db = 10*log10(peak_power/noise_floor)`
  - valid iff `peak_snr_db >= min_peak_snr_db` (default 6 dB)
  - retain up to `max_candidate_peaks` valid peaks per spectrum (default 5)
  - if none valid: reason `NO_VALID_PEAKS` and/or `SNR_LOW`

### 6.3) Merging and coupling

- E28 (MUST): De-duplicate peaks via hybrid spacing `min_spacing_hz(fi)=max(abs_hz, frac*fi)`; keep strongest peak per group; log grouping.
- E29 (MUST): Near-degenerate peaks are kept as separate candidates; mark coupled/multi-peak region with flags (`PSD_MULTI_PEAK`, `MULTI_MODE_SUSPECTED`); do not force merging into one.

### 6.4) Sub-bin refinement

- E30 (SHOULD): Sub-bin refinement is allowed and enabled by default when the peak is isolated and quality is acceptable; log bin vs refined frequency and refinement method.

---

## 7) Diagnostics

Source: `docs/specs_clarifications.md` F31-F38.

- F31 (MUST): Diagnostics are reported as numeric metrics plus flags/reason codes; thresholds are configurable and logged.
- F32 (MUST): Field-first priorities; core diagnostics focus on on-site usability + validity of `fi` and `zeta`.
- F33 (MUST): Provide both time-domain SNR per hit and frequency-domain SNR per peak.
- F34 (MUST): Beating detection metric + `BEATING_DETECTED` threshold.
- F35 (MUST): Envelope monotonicity metric + `ENVELOPE_NON_MONOTONIC` threshold.
- F36 (MUST): Instantaneous frequency stability metric + `INSTANT_FREQ_DRIFT` threshold.
- F37 (MUST): Filter ringing risk metric (`q_factor`) + `FILTER_RINGING_RISK` threshold.
- F38 (MAY): Sensitivity sweeps are nice-to-have; not required for v1.

---

## 8) Damping estimators

Source: `docs/specs_clarifications.md` G39-G46.

### 8.1) TD envelope fit (modal)

- G39 (MUST): TD damping baseline is Hilbert envelope + log-linear regression on per-peak bandpassed response.
- G40 (MUST): Compute both full-window fit and established-decay fit when possible; preserve both.
- G41 (MUST): `TOO_SHORT_DECAY` is frequency-aware (min duration + min cycles) with preset defaults.

### 8.2) FD half-power bandwidth (modal)

- G42 (MAY): Half-power bandwidth estimator is allowed; default is no extra PSD smoothing.
- G43 (MUST): If half-power points are not found cleanly, output `NOT_COMPUTED` (preferred) with explicit reason codes.

### 8.3) Energy decay (effective)

- G44 (MUST): Energy decay estimator uses a small set of proxies:
  - default: envelope-squared proxy `E(t)=e(t)^2`
  - optional: `E(t)=y_filt(t)^2`
  - velocity-squared proxies are out of scope for v1
- G45 (MUST): Conversion rules to `zeta` depend on proxy; log slopes/decay rates used.
- G46 (MUST): Energy estimates always carry `EFFECTIVE_DAMPING_ONLY`; they are effective damping, not guaranteed modal damping.

---

## 9) Status and reason codes

Source: `docs/specs_clarifications.md` H47-H51.

- H47 (MUST): Status mapping is deterministic and transparent.
- H48 (MUST): Reason codes are partitioned into hard failures vs soft failures.
- H49 (MUST): Multiple reason codes may coexist; no explicit priority ordering required for v1 beyond hard/soft mapping.
- H50 (MUST): Distinct `NOT_COMPUTED` status exists.
- H51 (MUST): REJECTED estimates may still show numeric values for transparency, but are excluded from aggregates by default.

Estimate result contract (minimum fields):

- `hit_id`
- `fi_bin_hz`, `fi_refined_hz` (refined may be empty)
- `method` (e.g. `TD_FILT`, `FD_HALF_POWER`, `ENERGY_ENVELOPE_SQ`)
- `zeta` (may be empty/NaN)
- `status` (`OK|WARNING|REJECTED|NOT_COMPUTED`)
- `reason_codes[]`
- `diagnostics{}` (named numeric metrics)

---

## 10) Best-guess policy (optional)

Source: `docs/specs_clarifications.md` I52-I55.

- I53 (MUST): Best guess is per (hit, peak `fi`).
- I52/I55 (MUST): Deterministic selection order + tie-break on quality metrics.
- I54 (MUST): Energy is best-guess only as fallback and must remain labeled `EFFECTIVE_DAMPING_ONLY`.

---

## 11) Aggregation across hits

Source: `docs/specs_clarifications.md` J56-J60.

- J56 (MUST): Group peaks across hits using the global peak list; stable `mode_id` values.
- J57 (MUST): Mode matching uses a hybrid tolerance `max(abs_hz, frac*fi)`; configurable and logged.
- J58/J59 (MUST): Provide robust stats and show OK-only and OK+WARNING aggregates.
- J60 (MUST): Keep separate mode groups; do not force a single global "mode 0".

---

## 12) Reporting and output contracts

Source: `docs/specs_clarifications.md` K61-K65.

- K61 (MUST): Generate preprocess report in both Markdown and PDF, with field go/no-go metrics, hit count, and timestamps.
- K62 (MUST): Generate a combined modal report in both Markdown and PDF, with per-hit sections.
- K63 (MUST): Per-hit sections include PSD with annotated peaks + per-(hit,fi) plots (cap at 5 peaks per hit).
- K64 (MUST): Emit machine-readable CSV outputs (long + best guess); JSON export is allowed/recommended.
- K65 (MUST): Output directory structure is stable and considered public contract.

---

## 13) Reproducibility

Source: `docs/specs_clarifications.md` L66-L68.

- L66 (MUST): Outputs include full analysis config (everything that can change results), in human-readable and machine-readable forms.
- L67 (MUST): Outputs include version stamp + git hash (if available) + run timestamp.
- L68 (MUST): Analysis is deterministic for a given input+config.

---

## 14) Limits and future-proofing

Source: `docs/specs_clarifications.md` M69-M71 and N72-N74.

- M69 (MUST): Presets exist (structures vs xylophone) and drive defaults; user can override.
- M70 (SHOULD): Warn on long WAVs; streaming/chunking is out-of-scope for v1.
- M71 (MUST): Clipping is detected and flagged; analysis continues by default with aggressive warnings.
- N72/N73 (MUST): Manual hit editing and >2 channel inputs are out-of-scope for v1.
- N74 (MUST): Provide a stable minimal JSON export schema (`analysis_results.json`) for future database integration.
