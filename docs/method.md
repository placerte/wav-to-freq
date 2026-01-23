# Method notes — wav‑to‑freq

This document describes the **signal processing and physical assumptions**
used to extract natural frequency and damping ratio from impact test data.

The intent is not to be academically exhaustive, but to be **explicit,
defensible, and repeatable** for field measurements on real structures.

---

## 1. Measurement model

### 1.1 Physical system

The tested structure is assumed to behave locally as a **linear,
lightly damped dynamic system** during the free‑decay portion of the response.

For most intended use cases (ground‑mounted PV structures):

- multiple modes may be present in the measured bandwidth,
- modal coupling may occur (beating / close peaks),
- nonlinearities (slip, friction, amplitude‑dependent damping) are neglected in this first implementation.

---

### 1.2 Excitation

An instrumented impact hammer approximates a **short‑duration impulse**.

In the frequency domain, this corresponds to broadband excitation,
allowing multiple modes to be excited simultaneously.
In practice, only the lowest / dominant mode is retained.

---

### 1.3 Measured signals

Two channels are recorded:

- **Hammer force** (input)
- **Structural response** (typically acceleration)

Both are sampled synchronously and stored in a two‑channel WAV file.

---

## 2. Signal preprocessing

### 2.1 Channel identification

Channel roles are selected explicitly (hammer vs response) in the UI.

Notes:

- This avoids hard-coding a channel ordering convention.
- Auto-identification may be added later, but v1 prioritizes explicit traceability.

---

### 2.2 Impact detection

Impacts are detected on the hammer channel using:

- amplitude thresholding,
- minimum separation time between hits,
- optional normalization.

Each detected impact defines a **candidate analysis window**.

---

### 2.3 Windowing

For each hit, a time window is extracted:

- small pre‑trigger (for baseline),
- post‑trigger long enough to capture several oscillation cycles.

The window length is a compromise between:

- sufficient decay duration,
- avoiding contamination from subsequent hits or noise floor.

---

## 3. Signal conditioning

### 3.1 Detrending and normalization

The response signal is:

- detrended (remove DC bias),
- optionally normalized for numerical stability.

---

### 3.2 Band‑pass filtering

A **band‑pass filter** is applied to isolate the dominant mode.

Purpose:
- suppress low‑frequency drift,
- suppress high‑frequency noise and secondary modes.

Filter characteristics are chosen conservatively:
- wide enough not to distort decay,
- narrow enough to stabilize envelope fitting.

This step is critical for robust damping estimation.

---

## 4. Modal parameter extraction

### 4.1 Frequency estimation

Candidate peak frequencies are estimated from Welch PSD peaks.

- Multiple candidate peaks may be retained per hit (default cap is small, e.g. 5), rather than forcing a single dominant frequency.
- Peaks that appear close together are kept and flagged as potentially coupled.

---

### 4.2 Damping model

For a lightly damped single‑degree‑of‑freedom system,
the free response envelope is approximated by:

x(t) = A · e^(−ζωₙ t) · cos(ω_d t + φ)

where:
- ζ is the damping ratio,
- ωₙ is the natural circular frequency,
- ω_d ≈ ωₙ√(1−ζ²)

---

### 4.3 Envelope extraction

The amplitude envelope is estimated using:

- analytic signal (Hilbert transform)  
  **or**
- peak‑tracking of successive oscillation maxima.

The envelope is fitted in the **logarithmic domain** to estimate decay rate.

---

### 4.4 Damping estimation

The tool computes multiple damping estimates per (hit, peak):

- Time domain (modal): Hilbert envelope log-fit on the band-passed response.
- Frequency domain (modal): half-power bandwidth from the PSD when the peak is isolated.
- Energy decay (effective): energy proxy decay (e.g. envelope-squared), always labeled effective damping.

Each estimate includes quality diagnostics and flags (reason codes) to indicate when assumptions are likely violated.

---

## 5. Aggregation across hits

Each impact produces an independent estimate of fn and ζ.

Across all accepted hits:
- mean values are reported,
- dispersion provides an internal consistency check.

This is essential for field data where individual hits may be imperfect.

---

## 6. Limitations and scope

Current limitations (by design):

- linear behavior assumed,
- no automatic forced single-number "best guess" in v1 (the report shows multiple candidates and methods),
- amplitude‑dependent damping not modeled,
- strong modal overlap is detected/flagged but not fully resolved in v1.

These choices favor **robust field deployment** over theoretical generality.

---

## 7. Intended evolution

Future extensions may include:

- explicit multi‑mode extraction,
- amplitude‑dependent damping models,
- automated window optimization,
- tighter coupling with wind‑induced dynamic analysis.

For now, the priority is:
**repeatability, transparency, and engineering usefulness**.
