# wav-to-freq

Extract **natural frequency (fn)** and **damping ratio (ζ)** from an instrumented hammer impact recorded as a **2‑channel WAV** (hammer force + structural response).  
The tool produces plots, CSV data, and Markdown/PDF reports suitable for **repeatable field surveys** and later database integration.

> Status: working v0.2.0 proof‑of‑workflow. The engineer workflow section is intentionally a placeholder until validated on real structures.

---

## What it does

Given a two‑channel WAV containing **multiple impacts**, `wav‑to‑freq`:

- detects individual hammer hits,
- extracts a response window for each hit,
- estimates modal parameters per hit (**fn**, **ζ**) with quality metrics,
- exports results as:
  - `modal_results.csv` (database‑friendly)
  - `modal_report.md` (+ optional `modal_report.pdf`)
  - per‑hit response plots (PNG)
  - preprocessing diagnostics (Markdown/PDF)

A reference dataset is provided:
- [`examples/aluminium-plate/`](examples/aluminium-plate)

---

## Installation

### Linux (recommended): pre‑built binary

```bash
curl -L -o wav-to-freq \
  https://github.com/placerte/wav-to-freq/releases/latest/download/wav-to-freq-linux-x86_64

chmod +x wav-to-freq
sudo mv wav-to-freq /usr/local/bin/wav-to-freq
```

### External dependencies (for PDF export)

Markdown reports work out of the box.  
**PDF export additionally requires**:

- **Pandoc**
- **LaTeX toolchain** (e.g. TeX Live)

Example (Debian / Ubuntu):

```bash
sudo apt-get install -y pandoc texlive-latex-base texlive-latex-recommended texlive-latex-extra
```

---

## How to use (placeholder)

This section will describe a **typical engineer workflow**, including:

- acquisition setup (Audacity / field recorder)
- channel conventions (hammer vs response)
- file naming and directory hygiene
- recommended hit spacing and count
- interpretation and rejection of bad hits

To be written after field validation.

---

## How it works

High‑level pipeline:

1. Read WAV and auto‑identify hammer / response channels.
2. Detect impacts and segment response windows.
3. Generate preprocessing diagnostics.
4. Extract modal parameters per hit.
5. Export reports and CSV results.

For architectural context:
- [`docs/packages.md`](docs/packages.md)

---

## The science behind it

A detailed technical description is provided here:
- **[`docs/method.md`](docs/method.md)**

It covers:
- signal assumptions and preprocessing
- frequency‑domain and time‑domain analysis
- damping extraction methodology
- practical limitations and field considerations

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

Tracked in:
- [`TODO.md`](TODO.md)

---

## Development workflow (v1 rewrite)

This repo is in an incremental rewrite toward the v1 spec.

- Agent/dev notes: `AGENTS.md`
- Normative spec: `docs/specs.md`
- Decision log: `docs/specs_clarifications.md`
- Architecture plan: `docs/implementation.md`
- V1 must-ship tracking: `docs/traceability_v1.md`
- Legacy reference during migration: `src/legacy/`
