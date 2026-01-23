# report_specs.md (v1) - Reporting Format & Decisions

This document defines the reporting strategy and output format for v1.

It complements:

- `docs/specs.md` (requirements)
- `docs/specs_clarifications.md` (rationale)
- `docs/implementation.md` (architecture plan)

---

## 1) Scope

Reporting covers these artifacts:

- `report_preprocess.md` (+ PDF)
- `modal_report.md` (+ PDF)
- `modal_results.csv`
- `modal_results_long.csv`
- `analysis_results.json`

---

## 2) General principles

- Show all computed estimates; never hide results.
- Use flags/reason codes to communicate reliability.
- Do not declare a single "best" estimator in the report.
- Keep numeric diagnostics visible but limited to a short, consistent list.

---

## 3) Modal report format

### 3.1 Summary section

- Total hits, accepted, rejected (per existing modal report)
- Short note explaining that flags indicate reliability
- Link to `modal_results_long.csv`
- Summary tables (see below)

### 3.2 Summary tables

Provide a compact hit-by-hit table focused on `fi` and `zeta`:

- Rows: hit IDs (H001, H002, ...)
- Columns: per-peak fields for the primary peak list (ranked peaks)
  - `fi` (Hz) per peak rank
  - `zeta_td` (TD envelope established fit) per peak rank
  - `zeta_fd` (FD half-power) per peak rank
  - `zeta_energy` (energy decay) per peak rank

Cells may be empty (`—`) when a method is not computed or a peak is absent.

If the number of peaks differs by hit, the table should expand to the maximum
observed peak rank and leave gaps for missing peaks.

The maximum number of peak ranks shown is configurable via `max_summary_peaks`
(default 5).

### 3.3 Per-hit detail (default: full)

For each hit:

- Header: `H###`
- Per-hit response plots:
  - time-domain response (raw + context)
  - frequency-domain response (PSD) with annotated peaks
- Per-peak sections (cap 5 peaks by default), each with:
  - filtered response for that peak
  - per-method subsections (TD envelope, FD half-power, energy decay)
    including status, flags/reason codes, and a method-specific diagnostic plot.

Recommended columns:

- Peak rank
- `fi_bin_hz`
- Method
- `zeta`
- Status (`OK|WARNING|REJECTED|NOT_COMPUTED`)
- Reason codes (comma-separated)
- Diagnostics (shortlist, below)

### 3.4 Diagnostics shortlist

Default diagnostics to show inline:

- `beating_score`
- `envelope_increase_frac`
- `inst_freq_rel_jitter`
- `filter_q_factor`
- `env_fit_r2`

All other diagnostics must still be present in `modal_results_long.csv`.

Notes (as-built):

- Method subsections are rendered even for `NOT_COMPUTED` estimates; the report should still show the status + reasons and (when possible) a plot to explain the failure.
- PDF export prefers LaTeX (`pdflatex`) for table layout and math; it falls back to HTML/WeasyPrint when LaTeX tooling is unavailable.

---

## 4) CSV outputs

### 4.1 `modal_results.csv`

Legacy per-hit summary (existing structure).

### 4.2 `modal_results_long.csv`

Long-form estimates, one row per (hit, peak, method):

- `hit_id`
- `peak_rank`
- `method`
- `fi_bin_hz`
- `fi_refined_hz`
- `zeta`
- `status`
- `reason_codes`
- `diagnostics{}` flattened

---

## 5) Flags and labels

- Coupling and beating flags are always shown (e.g., `PSD_MULTI_PEAK`, `BEATING_DETECTED`).
- Energy decay estimates always include `EFFECTIVE_DAMPING_ONLY`.
- Reports do not suppress any method; they only flag and describe.

---

## 6) Future additions

- Add a summary table grouped by method (mean/min/max, OK-only vs OK+WARNING).
- Add contextual tips for when a method is recommended (without enforcing a choice).
