# specs.md — Dynamic damping & frequency identification from impact tests

## 1. Purpose

This software analyzes impact-hammer vibration tests (hammer + accelerometer)
to extract:

- Dominant natural frequencies
- Damping estimates (ζ)
- Diagnostic information about modal purity, coupling, and reliability

The goal is **not** to force a single number, but to:
- compute multiple mathematically valid estimates,
- expose their assumptions,
- flag when those assumptions are violated,
- and provide an educated diagnosis suitable for engineering judgment and future databases.

---

## 2. Scope

### In scope
- 2-channel WAV input (hammer + response)
- Multi-hit detection
- Time-domain and frequency-domain analysis
- Multiple damping estimators
- Diagnostic plots and flags
- Per-hit and aggregate reporting

### Out of scope (for now)
- Full multi-modal system identification (ERA/SSI/OMA)
- Nonlinear / amplitude-dependent damping modeling
- Mode shape extraction

---

## 3. Core philosophy

1. **Compute broadly, interpret explicitly**
   - All relevant estimators are computed whenever possible.
   - No estimator is silently preferred or discarded.

2. **Assumptions are never hidden**
   - Every damping estimate carries applicability, reliability, and reason codes.

3. **Numbers do not imply truth**
   - A numeric ζ may be printed even when rejected, but always with status labels.

4. **Diagnostics are first-class outputs**
   - Beating, coupling, and multi-mode behavior are valuable results.

---

## 4. Terminology

- **Hit**: one detected hammer impact and associated response window.
- **Candidate peak (fi)**: a frequency peak detected in the PSD/Welch spectrum.
- **Single-mode compatible**: signal behavior consistent with one dominant mode.
- **Beating**: amplitude modulation caused by multiple close frequencies.
- **Modal damping (ζn)**: damping associated with a single vibration mode.
- **Effective damping**: energy decay rate when multiple modes contribute.

---

## 5. Per-hit analysis workflow (conceptual)

For each hit:

1. Extract windowed raw response.
2. Compute PSD/Welch spectrum.
3. Detect candidate frequency peaks (max N, default N = 5).
4. For each candidate peak:
   - Apply band-pass filtering around fi.
   - Compute diagnostics (beating, stability, etc.).
   - Compute damping estimates using multiple methods.
5. Assign quality/status labels to each estimate.
6. Produce an optional “best guess” based on all computed data.

---

## 6. Frequency estimation

For each hit:
- PSD/Welch is computed on the response signal.
- Peaks are detected using prominence and noise-floor criteria.
- Peaks closer than a minimum spacing may be merged.
- Each peak fi is treated as a candidate mode.

Frequency repeatability across hits is reported separately from damping quality.

---

## 7. Damping estimation methods

All methods are computed when mathematically possible.

### 7.1 Time-domain envelope / log decrement
- Applied to:
  - raw response
  - filtered response around fi
- Assumes single-mode exponential decay.

### 7.2 Frequency-domain half-power bandwidth
- Computed from PSD around fi.
- Less sensitive to time-domain beating.
- Still assumes modal isolation.

### 7.3 Energy decay method
- Based on decay of vibrational energy proxy:
  - velocity² (from integrated acceleration)
- More robust to modal beating.
- Represents **effective damping**, not pure modal ζ.

---

## 8. Diagnostics (computed for each hit and each fi)

Diagnostics are computed independently of damping estimation.

### Examples (non-exhaustive)
- Envelope monotonicity
- Beating / amplitude modulation score
- Instantaneous frequency stability
- PSD multi-peak presence
- SNR estimate
- Filter dominance / ringing risk
- Sensitivity of ζ to small parameter changes

Diagnostics are numeric internally and summarized as flags in reports.

---

## 9. Estimate status classification

Every damping estimate is wrapped in a structured result:

- `value`: numeric ζ
- `method`: TD_raw, TD_filt, FD_half_power, Energy, etc.
- `target_frequency`: fi
- `status`: OK | WARNING | REJECTED
- `reason_codes`: list of strings
- `diagnostics`: supporting metrics

### Status meanings

#### OK
- Method assumptions are satisfied.
- ζ is physically interpretable.

#### WARNING
- Assumptions partially violated.
- ζ is indicative but uncertain.

#### REJECTED
- Assumptions clearly violated.
- ζ has no physical meaning and must not be used for decisions.

---

## 10. Reason codes (initial set)

### Signal quality
- SNR_LOW
- CLIPPED_SIGNAL

### Modal purity
- BEATING_DETECTED
- MULTI_MODE_SUSPECTED
- PSD_MULTI_PEAK

### Fit / decay validity
- ENVELOPE_NON_MONOTONIC
- INSTANT_FREQ_DRIFT
- TOO_SHORT_DECAY

### Filter issues
- FILTER_RINGING_RISK
- FILTER_BAND_TOO_NARROW
- FILTER_SENSITIVITY_HIGH

### Method limitations
- EFFECTIVE_DAMPING_ONLY

---

## 11. Best-guess selection (optional, automated)

A per-hit “best guess” ζ may be selected for convenience:

1. Prefer estimates with status OK
2. Else prefer WARNING
3. Else no best guess is reported

Selection order and rationale must be documented and reproducible.
Manual override must be explicitly labeled as such.

---

## 12. Reporting requirements

Per hit, the report MUST show:
1. Raw windowed response (time)
2. PSD/Welch with detected peaks
3. Filtered response for primary peak
4. Table of damping estimates with status labels and reasons

Optional (debug):
- Filtered responses for other peaks
- Detailed diagnostic plots

Summary statistics MUST:
- Exclude REJECTED estimates
- Clearly separate OK and WARNING values
- Never average mixed-quality results silently

---

## 13. Interpretation rules (normative)

- A numeric ζ without an OK status MUST NOT be treated as a reliable material or structural property.
- Beating after band-pass filtering SHALL be interpreted as evidence of modal coupling, not noise.
- Energy-based ζ SHALL be labeled as effective damping when multiple modes participate.

---

## 14. Design intent

This specification prioritizes:
- Physical correctness over simplicity
- Transparency over automation
- Diagnostic power over forced conclusions

The software is intended to assist expert judgment, not replace it.

