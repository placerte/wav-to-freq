# Aluminum Plate Impact Test — Reference Example

This directory contains a **reference impact-testing example** performed on a simple aluminum plate.  
It serves as a **sanity check and validation case** for the `wav-to-freq` processing pipeline before applying it to full-scale PV racking structures.

The goal of this example is **not structural realism**, but:

- verifying signal acquisition,
- validating hit detection,
- inspecting transient response quality,
- and confirming modal post-processing behavior.

---

## Test object

- **Specimen**: Flat aluminum plate  
- **Purpose**: Simple, repeatable, high signal-to-noise test article  
- **Expected behavior**:
  - Clear impulse response
  - Dominant low-order modes
  - Minimal nonlinear effects

This type of object behaves similarly to a *“xylophone bar”* and is well suited for early-stage modal testing.

---

## Measurement setup (high level)

- **Excitation**: Instrumented impact hammer
- **Response**: Accelerometer mounted on the plate
- **Acquisition**:
  - Two-channel WAV recording
    - Channel 1: hammer force
    - Channel 2: structural response
- **Processing assumptions**:
  - Linear behavior
  - Low-amplitude excitation
  - Focus on fundamental mode(s)

Exact hardware details are documented elsewhere in the project.

---

## Directory structure

# Aluminum Plate Impact Test — Reference Example

This directory contains a **reference impact-testing example** performed on a simple aluminum plate.  
It serves as a **sanity check and validation case** for the `wav-to-freq` processing pipeline before applying it to full-scale PV racking structures.

The goal of this example is **not structural realism**, but:

- verifying signal acquisition,
- validating hit detection,
- inspecting transient response quality,
- and confirming modal post-processing behavior.

---

## Test object

- **Specimen**: Flat aluminum plate  
- **Purpose**: Simple, repeatable, high signal-to-noise test article  
- **Expected behavior**:
  - Clear impulse response
  - Dominant low-order modes
  - Minimal nonlinear effects

This type of object behaves similarly to a *“xylophone bar”* and is well suited for early-stage modal testing.

---

## Measurement setup (high level)

- **Excitation**: Instrumented impact hammer
- **Response**: Accelerometer mounted on the plate
- **Acquisition**:
  - Two-channel WAV recording
    - Channel 1: hammer force
    - Channel 2: structural response
- **Processing assumptions**:
  - Linear behavior
  - Low-amplitude excitation
  - Focus on fundamental mode(s)

Exact hardware details are documented elsewhere in the project.

---

## Directory structure

examples/aluminium-plate
├── aluminum_plate_impact_test.md # this document
├── input
│ └── hit_251212-2.wav # raw acquisition file
└── output
└── hit_251212-2
├── figures
│ ├── overview_two_channels.png
│ └── hits
│ ├── H001_response.png
│ ├── H002_response.png
│ └── ...
├── modal_report.md
├── modal_report.csv
└── report_preprocess.md

---

## Input data

### `input/hit_251212-2.wav`

- Raw two-channel recording
- Contains multiple hammer impacts in a single file
- Used as input to the full processing pipeline

---

## Output artifacts

### Preprocessing report

**`report_preprocess.md`**

- Overview of detected impacts
- Signal conditioning steps
- Channel identification and validation
- Hit segmentation diagnostics

### Hit-level response plots

**`figures/hits/Hxxx_response.png`**

- Individual impulse responses
- Used to visually assess:
  - impact quality
  - noise floor
  - decay behavior
  - repeatability across hits

### Overview plot

**`figures/overview_two_channels.png`**

- Full-length signal view
- Hammer vs response channel comparison
- Useful for quick sanity checks

### Modal results

**`modal_report.md`**

- Human-readable summary of modal extraction results
- Frequencies and damping estimates
- Notes on confidence and consistency

**`modal_report.csv`**

- Machine-readable version of modal results
- Intended for:
  - aggregation
  - database ingestion
  - comparison across tests

---

## Why this example exists

This aluminum plate test is intended to be:

- ✅ **Simple**
- ✅ **Repeatable**
- ✅ **Well-behaved**

It provides a baseline reference against which:

- code changes,
- algorithm updates,
- and reporting modifications

can be validated before moving to **real-world PV racking structures**, where geometry, boundary conditions, and excitation are far more complex.

---

## Next steps

- Compare extracted modal parameters against analytical or reference values.
- Repeat test with different impact locations and sensor positions.
- Use this example as a template for future field-test documentation.
