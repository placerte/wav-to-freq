# envelope-decay-fit — specs.md

## Purpose

Standalone utility to fit exponential decay curves to a **time-domain response envelope** `env(t)` and expose **damping ratio ζ** in the reported parameters.

This module is intentionally isolated for rapid development/testing and will later be integrated into the larger `wav-to-freq` application.

## Scope (locked)

- Input is **pre-formatted** envelope data: `(t, env)` only.
- Natural frequency **`f_n` is provided** (required input).
- The utility computes multiple fit methods and **reports all** results; it does not auto-pick “truth”.
- Piecewise exponential fitting is supported with **user-provided piece count** (default `n_pieces=2`).
- Tail trimming is supported and is applied **before** window expansion.

## Definitions and model

### Provided frequency
- `f_n` in Hz is provided by caller.
- `ω_n = 2π f_n` in rad/s.

### Exponential decay rate and damping
We fit decay rate `α` (1/s) and derive:

- `ζ = α / ω_n`

### Per-window curve forms

All window fits are parameterized in a well-posed way (no free-floating `t0`).

Let `t_ref = t_start` of the current window.

- **LOG fit** (no floor, log-domain):
  - Model: `ln(env(t)) ≈ b - α (t - t_ref)`
  - Requires strictly positive `env` samples in the window (window may be marked invalid otherwise).

- **LIN0 fit** (linear-domain, no floor):
  - Model: `env(t) ≈ A * exp(-α (t - t_ref))`

- **LINC fit** (linear-domain, with floor):
  - Model: `env(t) ≈ A * exp(-α (t - t_ref)) + C`

Notes:
- `t0` is not fitted as an independent parameter. If a “t0-like” value is later desired for reporting, it must be derived (not a free parameter).

## High-level algorithm

### 0) Optional tail trimming (auto)
If enabled, determine a trimmed effective end time/index `t_end_used` / `i_end_used` using a robust floor estimate from the tail:

- Tail probe: last `tail_probe_s` seconds (or a default derived from signal length).
- Robust floor: `floor_med = median(env_tail)`, `floor_mad = MAD(env_tail)`.
- Cut level: `cut_level = floor_med + tail_k_mad * floor_mad`.
- Determine `i_end_used` as the last index such that `env` remains above `cut_level` for at least `tail_min_run_s`.
- All subsequent windows end at `i_end_used`.

Emit flags such as:
- `TAIL_TRIM_APPLIED`
- `TAIL_FLOOR_DOMINANT`

Store `floor_med`, `floor_mad`, `cut_level`, `t_end_used`.

### 1) Piece extraction (repeat for requested pieces)
Let current piece end index be `i_end`.

For each piece (starting from late-time segment):
1. Build a sequence of expanding windows by moving the start index backward:
   - Window k: `[i_start_k, i_end]` with `i_start_k = i_end - k + 1`
   - Start with `k=2` samples and expand until `i_start_k` reaches 0 (or remaining data boundary).
2. For each window, compute and record:
   - LOG fit
   - LIN0 fit
   - LINC fit
   Along with scores and validity.
3. From the primary score trace `R²_log(Δt)`, propose a breakpoint using **change-point detection** (two-regime split):
   - Smooth `R²_log` lightly.
   - Find split index that best matches a “late stable regime” vs “earlier degraded regime” (minimize SSE of two segments).
   - Apply constraints (minimum duration in the established regime; avoid selecting breakpoint in extreme tail).
4. The suggested breakpoint defines the piece start index `i_start_piece`. The extracted piece is:
   - `piece = [i_start_piece, i_end]`
5. The representative per-piece parameters for each method (LOG/LIN0/LINC) are taken from the fit on this final extracted piece window.
6. Update `i_end = i_start_piece` and repeat for next piece until:
   - `n_pieces` reached, or
   - insufficient remaining samples (emit flags, return fewer pieces).

### 2) Directionality (locked)
Each piece is extracted by **backward-expanding from its own end**, not forward.

## Variable naming (locked)

Prefer window duration as the independent variable for traces:
- `Δt = t_end - t_start` (seconds)

Traces:
- **Score trace** / **fit-quality trace**: e.g. `R²_log(Δt)`, `R²_lin0(Δt)`, `R²_linc(Δt)`
- **Parameter trace**: e.g. `ζ_log(Δt)`, `ζ_linc(Δt)`, `C_linc(Δt)`

Segment naming:
- Late segment: `established_free_decay` (aka quasi-single-mode decay)
- Early segment: `transient_dominated_decay` (aka coupled / non-stationary decay)

## Outputs (locked)

The utility returns a programmatic result object always.
Disk outputs are optional (controlled by `out_dir`).

### Programmatic return
Return a single result object containing:
- input arrays: `t`, `env`
- provided frequency: `f_n`, derived `ω_n`
- trimming info (if applied)
- `windows_trace`: list/array of per-window fit records
- `pieces`: list of piece records (<= requested count)
- `flags`: list of structured flags (scope + severity + code + message)
- `artifacts`: written file paths if `out_dir` set

### Optional disk artifacts (when `out_dir != None`)
Write:
- `envelope.csv`
- `windows_trace.csv`
- `pieces.csv`
- `flags.csv`
- `summary.csv`
- `plots/` images (PNG)

#### envelope.csv
- `idx`, `t_s`, `env`

#### windows_trace.csv (one row per expanding window)
Window identity:
- `win_id`, `i_start`, `i_end`, `t_start_s`, `t_end_s`, `dt_s`, `n_points`

LOG block:
- `alpha_log`, `zeta_log`, `r2_log`, `rmse_log`, `valid_log`, `notes_log`

LIN0 block:
- `alpha_lin0`, `zeta_lin0`, `r2_lin0`, `rmse_lin0`, `valid_lin0`, `notes_lin0`

LINC block:
- `alpha_linc`, `zeta_linc`, `C_linc`, `r2_linc`, `rmse_linc`, `valid_linc`, `notes_linc`

Tail-trim diagnostics columns (if applicable):
- `floor_med`, `floor_mad`, `cut_level`, `t_end_used_s`

#### pieces.csv
Per piece:
- `piece_id`, `label`, `i_start`, `i_end`, `t_start_s`, `t_end_s`, `dt_s`
- breakpoint meta: `break_confidence` (optional), `break_reason`

Per-method representative fit on the extracted piece window:
- LOG: `zeta_log_piece`, `alpha_log_piece`, `r2_log_piece`, `rmse_log_piece`, `valid_log_piece`
- LIN0: `...`
- LINC: `...`, plus `C_linc_piece`

#### flags.csv
- `scope` (`window` or `piece` or `global`)
- `scope_id`
- `severity` (`info|warn|reject`)
- `code`
- `message`
- `details` (optional)

#### summary.csv
Single-row quick view:
- `f_n_hz`, `n_samples`, `t_total_s`, `n_pieces_requested`, `n_pieces_returned`
- `tail_trim_applied`, `t_end_used_s`
- `notes`

### Plots (PNG)
- `plots/piecewise_fit.png`:
  - envelope curve + piecewise fitted curves
  - small annotation box with top flags and per-piece ζ values (avoid clutter)
- Recommended diagnostics:
  - `plots/trace_scores.png`: R² traces vs Δt with breakpoint markers
  - `plots/trace_params.png`: ζ traces vs Δt (and C trace if helpful)

## Flags (examples, non-exhaustive)

- `TAIL_TRIM_APPLIED` (info)
- `TAIL_FLOOR_DOMINANT` (warn)
- `INSUFFICIENT_SAMPLES` (reject)
- `NO_BREAKPOINT_FOUND` (warn/reject)
- `NO_STABLE_REGION` (warn/reject)
- `LOG_INVALID_NONPOSITIVE_ENV` (warn)
- `ZETA_UNSTABLE_IN_ESTABLISHED_SEGMENT` (warn)

## Configuration / API (draft)

Required:
- `t: array[float]` (seconds, monotonic increasing)
- `env: array[float]` (>= 0 expected)
- `f_n_hz: float`

Optional:
- `n_pieces: int = 2`
- `out_dir: Path | None = None`

Tail trim options:
- `tail_trim_mode: "off" | "auto" | "fixed" = "auto"`
- `tail_probe_s: float`
- `tail_k_mad: float`
- `tail_min_run_s: float`
- `t_end_max_s: float` (if fixed)

Breakpoint detection options (v1 defaults acceptable):
- smoothing parameters for `R²_log` trace
- minimum established duration constraint (e.g., in seconds or cycles of f_n)

## Non-goals (v1)

- Envelope extraction from raw waveform (Hilbert, rectified+LPF, etc.)
- Automatic head trimming / hit start detection
- Automatic selection of a single “best” ζ across methods

