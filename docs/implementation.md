# implementation.md (v1) - Code Architecture Plan

This document describes the intended **v1 implementation architecture** for `wav-to-freq`.

It is designed to be:

- approachable for non-software-specialists (mechanical engineer friendly)
- simple, explicit, and testable
- consistent with `docs/specs.md`

The decision log lives in `docs/specs_clarifications.md`.

---

## 0) Design principles

1) Simple Python, not "framework" architecture

- No MVVM/DDD frameworks.
- Use plain dataclasses, small functions, and explicit data flow.
- Avoid clever abstractions unless they remove real duplication.

2) Small files, small functions

- Prefer files in the ~100-250 line range.
- Prefer functions that fit on one screen and do one thing.
- Use descriptive names (more important than comments).

3) Pure computation is separated from I/O

- `analysis/*` should be pure/deterministic and easy to unit test.
- `io/*` reads WAVs and prepares hit windows.
- `reporting/*` writes MD/PDF/CSV/JSON.
- UI calls into the pipeline but does not contain math.

4) "Show the thing"

- The code must represent coupled/multi-peak cases as first-class outputs.
- The code must not collapse multiple peaks into one silent decision.

---

## 1) Top-level pipeline

The pipeline is intentionally explicit:

1. Load stereo WAV + channel roles (`io/wav_reader.py`)
2. Detect hits on hammer channel (`io/hit_detection.py`)
3. Extract per-hit windows (`io/hit_windows.py` or part of hit_detection)
4. Generate preprocess report (field go/no-go) (`reporting/preprocess/*`)
5. Modal analysis (multi-peak, multi-estimator) (`analysis/*`)
6. Aggregate across hits into mode groups (`analysis/aggregation/*`)
7. Generate modal report + machine outputs (`reporting/modal/*`)

The UI calls a single entry point like:

`pipeline/run.py:run_analysis(wav_path, out_dir, config)`

---

## 2) Package layout (v1 target)

Keep the existing top-level package name: `wav_to_freq`.

```
src/wav_to_freq/
  app/
    tui_app.py
    tui_help.py
  config/
    presets.py
    model.py
  domain/
    enums.py
    reason_codes.py
    results.py
    types.py
  io/
    wav_reader.py
    hit_detection.py
    hit_windows.py
  dsp/
    filters.py
    psd.py
    smooth.py
    stats.py
  analysis/
    peaks/
      global_peaks.py
      per_hit_peaks.py
      merge.py
    diagnostics/
      beating.py
      monotonicity.py
      inst_freq.py
      filter_risk.py
    estimators/
      td_envelope.py
      fd_half_power.py
      energy_decay.py
    status/
      mapping.py
    aggregation/
      grouping.py
      summary_stats.py
  reporting/
    context.py
    markdown.py
    plots/
      preprocess.py
      modal.py
    writers/
      preprocess.py
      modal.py
      csv.py
      json.py
      pdf.py
  pipeline/
    run.py

src/legacy/
  (previous modules moved here during migration)
```

Notes:

- This layout is intentionally "boring": files are grouped by what they do.
- Each `analysis/*` file should be small and focused.

---

## 3) Core data model (dataclasses)

We should represent the v1 spec outputs directly.

### 3.1 Input and windows

- `StereoWav` (existing; keep)
- `HitWindow`
  - `hit_id`, `t_hit_s`
  - `t_start_s`, `t_end_s` (absolute time)
  - `hammer[]`, `response[]` arrays

### 3.2 Spectral objects

- `PsdResult`
  - `f_hz[]`, `pxx[]`
  - `noise_floor` (E26)
  - `psd_config` snapshot

- `PeakCandidate`
  - `fi_bin_hz`
  - `fi_refined_hz` (optional)
  - `peak_power`, `noise_floor`, `peak_snr_db` (E27)
  - `is_global` (E24)
  - `peak_detection_count` (optional; number of hits contributing when hit-local aggregation is enabled)
  - `detection_ratio` (optional; derived `peak_detection_count / total_hits`)
  - `flags[]` (e.g. coupled region)

### 3.3 Diagnostics and estimates

- `DiagnosticValue`
  - `name`, `value` (float or None), `flag` (optional reason code)

- `Estimate`
  - `method` (string enum)
  - `fi_hz` (target)
  - `zeta` (float or None)
  - `status` (`OK|WARNING|REJECTED|NOT_COMPUTED`)
  - `reason_codes[]`
  - `diagnostics{}`

### 3.4 Results containers

- `HitResult`
  - `hit_id`, `t_hit_s`
  - `psd_per_hit`
  - `peaks[]` (max 5 by default)
  - `estimates_by_peak` (peak -> list[Estimate])
  - `best_guess_by_peak` (peak -> Estimate or None)

- `RunResult`
  - input metadata
  - config snapshot (L66)
  - `hit_results[]`
  - aggregated mode groups

---

## 4) Status + reason codes

### 4.1 Status enum

- `OK`
- `WARNING`
- `REJECTED`
- `NOT_COMPUTED`

The v1 mapping rules are in `docs/specs.md` (H47-H51).

### 4.2 Reason codes

Reason codes are plain strings (or an Enum), but must be stable because they are part of outputs.

Implement in `domain/reason_codes.py`.

---

## 5) Interfaces (simple, not fancy)

Avoid plugin frameworks. Use small, explicit call patterns.

### 5.1 Peak detection

- `analysis/peaks/global_peaks.py:compute_global_peak_list(hit_windows, config) -> list[PeakCandidate]`
- `analysis/peaks/per_hit_peaks.py:compute_hit_peaks(hit_window, global_peaks, config) -> list[PeakCandidate]`

Global peak selection should run a full-band pass plus a low-frequency pass (default 1–100 Hz with a 3 dB SNR gate) and merge them before de-duplication, so low-frequency structural modes are not suppressed by higher-energy peaks. Optionally add a hit-local union pass that keeps peaks appearing in at least `min_hits` hits (default 2), using a 3 dB SNR gate.

### 5.2 Diagnostics

Each diagnostic module exposes one function:

- `compute_beating_score(y_filt, fs, ...) -> (score, flag)`

Diagnostics are added to estimates (and to reports) in a single place.

### 5.3 Estimators

Each estimator module exposes one function:

- `estimate_td_envelope(hit, peak, config) -> Estimate`
- `estimate_fd_half_power(hit, peak, config) -> Estimate`
- `estimate_energy_decay(hit, peak, config) -> Estimate`

Estimators must:

- be deterministic
- return `NOT_COMPUTED` rather than raising, when prerequisites are missing
- attach diagnostics and reason codes

As-built status (2026-01-23):

- Implemented estimator modules: `src/wav_to_freq/analysis/estimators/td_envelope.py`, `src/wav_to_freq/analysis/estimators/fd_half_power.py`, `src/wav_to_freq/analysis/estimators/energy_decay.py`.
- Implemented common diagnostics and deterministic status mapping in the estimator pipeline: `src/wav_to_freq/analysis/estimators/pipeline.py`, `src/wav_to_freq/analysis/status/mapping.py`.
- Reporting was refactored to a format-agnostic doc model and LaTeX-first PDF export: `src/wav_to_freq/reporting/doc.py`, `src/wav_to_freq/reporting/renderers/*`, `src/wav_to_freq/reporting/writers/pdf.py`.

#### Zeta pipeline plan (rewrite)

Goal: implement the full zeta (damping) workflow defined in specs G39-G46.

1) TD envelope fit (modal) (`analysis/estimators/td_envelope.py`)

- Inputs: hit window, target peak, config, and per-peak band-pass settings (D19/D20).
- Compute analytic envelope (Hilbert) on band-passed response.
- Produce two fits per peak when possible:
  - full-window fit
  - established-decay fit
- Enforce frequency-aware guards (G41): `decay_min_duration_s` + `decay_min_cycles`.
- Report fit diagnostics (slope, intercept, `env_fit_r2`) and reason codes on failure.

2) FD half-power bandwidth (optional) (`analysis/estimators/fd_half_power.py`)

- Use per-hit PSD (E25) and per-peak isolation to compute 3 dB bandwidth.
- If crossings are not found or coupled regions are present, return NOT_COMPUTED with reason codes (G43).

3) Energy decay (effective) (`analysis/estimators/energy_decay.py`)

- Implement envelope-squared proxy by default; optionally signal-squared.
- Convert decay rate to zeta with proxy-specific formulae (G45).
- Always attach `EFFECTIVE_DAMPING_ONLY` reason code.

4) Status mapping (`analysis/status/mapping.py`)

- Map hard/soft reason codes to `OK|WARNING|REJECTED|NOT_COMPUTED` (H47-H51).
- Apply mapping consistently across estimators and report outputs.

5) Wiring + reporting

- Per hit, per peak: compute estimator set, attach diagnostics + reason codes.
- Preserve both full-window and established-decay results.
- Expose `best_guess_by_peak` selection rules (I52-I55) after status mapping.

### 5.4 Status mapping

- `analysis/status/mapping.py:assess_estimate(estimate) -> estimate`

This is where hard/soft reason codes map to status, per H47/H48.

---

## 6) Reporting contracts

Reporting requirements are in `docs/specs.md` K61-K65.

v1 outputs (required):

- `report_preprocess.md` + `report_preprocess.pdf`
- `modal_report.md` + `modal_report.pdf`
- `modal_results_long.csv`
- `modal_results_best_guess.csv`
- `analysis_results.json` (N74)

Directory contract is part of the public API (K65).

---

## 7) Testing strategy (v1)

Keep this lightweight but meaningful.

1) Unit tests for deterministic math

- PSD noise floor percentile (E26)
- peak SNR gating (E27)
- peak merging (E28)
- envelope-fit conversion math (G45)
- status mapping rules (H47-H51)

2) Golden-output tests for contracts

- output directory filenames (K65)
- CSV column headers and required fields (K64)
- JSON schema keys (N74)

---

## 8) Migration plan (module-by-module)

We will not rewrite everything at once.

Rule:

- When replacing a module, move the old file into `src/legacy/` and leave a short README note.

Recommended implementation order (field value first):

1) Domain model (status/reason codes/results)
2) Peak list + noise floor + SNR gating (E24-E29)
3) Coupling diagnostics (F34-F37)
4) Energy effective damping (G44-G46)
5) Status mapping (H47-H51)
6) Reporting + machine outputs contracts (K64/K65/N74)
