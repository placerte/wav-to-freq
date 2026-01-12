# wav-to-freq

Extract **natural frequency (fn)** and **damping ratio (ζ)** from an instrumented hammer impact recorded as a **2-channel WAV** (hammer force + structural response). Generates a small set of artifacts (plots + CSV + Markdown/PDF reports) intended for repeatable field surveys and database ingestion.

> Status: working v0.2.0 proof-of-workflow. The “engineer workflow” section below is intentionally a placeholder until field usage is finalized.

---

## What it does

Given a two-channel WAV that contains **multiple impacts**:

- detects individual hits (segmentation),
- extracts a time window around each hit,
- estimates modal parameters per hit (**fn**, **ζ**) and fit quality metrics,
- exports results as:
  - `modal_results.csv` (for aggregation / database)
  - `modal_report.md` (+ optional `modal_report.pdf`)
  - per-hit response plots (PNG)
  - a preprocessing report (Markdown/PDF) with signal overview + hit detection diagnostics

A reference example is included:

- `examples/aluminium-plate/`

---

## Installation

### Linux (recommended): pre-built binary

```bash
curl -L -o wav-to-freq \
  https://github.com/placerte/wav-to-freq/releases/latest/download/wav-to-freq-linux-x86_64

chmod +x wav-to-freq
sudo mv wav-to-freq /usr/local/bin/wav-to-freq
```

### External dependencies (for PDF export)

Markdown reports can be generated without extra tools, but **PDF export requires**:

- Pandoc
- a LaTeX toolchain (e.g., TeX Live)

Example (Debian/Ubuntu):

```bash
sudo apt-get update
sudo apt-get install -y pandoc texlive-latex-base texlive-latex-recommended texlive-latex-extra
```

---

## How to use (placeholder)

This section will become a “typical engineer workflow” once validated on site.

Planned content:

- acquisition workflow (Audacity / recorder settings)
- channel conventions (hammer on channel 1, response on channel 2, etc.)
- file naming + directory hygiene
- recommended recording length / number of hits / spacing
- how to interpret the reports and reject bad hits

For now, see:

- `examples/aluminium-plate/`

---

## How it works

High-level pipeline:

1. Read WAV and identify channels.
2. Detect impacts and segment response windows.
3. Generate preprocessing diagnostics.
4. Extract modal parameters per hit.
5. Export reports and CSV results.

Architecture overview:

- `docs/packages.md`

---

## The science (short version)

An impact hammer approximates an impulse input, exciting the structure’s modes.
After the impact, the response is dominated by free decay of lightly damped modes.

This project currently targets:

- linear behavior
- dominant mode (mode 0)
- repeatable field measurements

See `docs/method.md` for details.

---

## Outputs

```
out_dir/
  report_preprocess.md
  report_preprocess.pdf
  modal_report.md
  modal_report.pdf
  modal_results.csv
  figures/
    overview_two_channels.png
    hits/
      H001_response.png
      ...
```

---

## TODOs / roadmap

See `TODO.md`.
