# Checkpoints

Lightweight audit trail for the v1 rewrite.

Goal:

- Record when a set of spec items was implemented and verified.
- Keep this human-readable and low-overhead.
- Git remains the source of truth; this file is a convenience index.

Conventions:

- Always include the git commit hash.
- List spec IDs that were implemented or materially changed.
- List what was actually run (tests/format/typecheck).

---

## 2026-01-21

- Commit: `4838828`
- Scope: v1 spec + rewrite workflow docs
- Specs covered:
  - Replaced `docs/specs.md` with v1 normative spec referencing clarification IDs
  - Added `docs/implementation.md` (architecture plan)
  - Added `docs/traceability_v1.md` (must-ship v1 tracking)
  - Added `AGENTS.md` and linked workflow from `README.md`
- Verification:
  - Documentation-only change

- Commit: `8e01327`
- Scope: v1 domain model foundation + initial unit tests
- Specs covered:
  - H50 (NOT_COMPUTED status introduced)
  - H48 (reason-code hard/soft sets introduced)
  - Supporting types for E/K/N outputs (`ReasonCode`, `EstimateStatus`, `EstimateResult`)
- Verification:
  - `python3 -m pytest -q` (passed)

- Commit: `a41ecef`
- Scope: v1 PSD peak helpers (noise floor, peak SNR gating, merging, coupled flags)
- Specs covered:
  - E26 (percentile noise floor)
  - E27 (peak_snr_db gating + cap N)
  - E28 (peak de-duplication)
  - E29 (coupled-region flags)
  - E24/E25 partially (global/per-hit peak APIs and Welch wrapper exist; not wired into pipeline yet)
- Verification:
  - `python3 -m pytest -q` (passed)

- Commit: `cf5d1a1`
- Scope: first real-WAV regression test (free srl2 1)
- Specs covered:
  - Sanity check evidence for B5/B7 + frequency pipeline behavior
- Verification:
  - `uv sync --group dev`
  - `uv run black .`
  - `uv run pytest -q` (passed)

## 2026-01-22

- Commit: `a86021c`
- Scope: global peak list low-band + hit-local union + detection counts
- Specs covered:
  - E24 (low-band + hit-local aggregation + detection count fields)
- Verification:
  - `uv run pytest -q tests/test_regression_free_srl2_1.py`

- Commit: `36751cb`
- Scope: SRP rail regression tests
- Specs covered:
  - Regression coverage for SRP samples
- Verification:
  - `uv run pytest -q tests/test_regression_free_srp_1.py tests/test_regression_free_srp_2.py tests/test_regression_free_srp_3.py tests/test_regression_free_srp_4.py`

- Commit: `66d53d7`
- Scope: plate regression tests (A1H3/A2H4/A3H1)
- Specs covered:
  - Regression coverage for plate samples
- Verification:
  - `uv run pytest -q tests/test_regression_free_plate_a2h4.py tests/test_regression_free_plate_a1h3.py tests/test_regression_free_plate_a3h1.py`

- Commit: `2a1f930`
- Scope: FD half-power estimator flags + reporting note
- Specs covered:
  - G42/G43 (half-power estimator)
  - F31 (flags in reports)
- Verification:
  - `uv run pytest -q tests/test_estimators_fd_half_power.py tests/test_regression_free_plate_a1h3.py`

- Commit: `128ed89`
- Scope: TD envelope estimator module
- Specs covered:
  - G39/G40/G41 (TD envelope estimator scaffold)
- Verification:
  - `uv run pytest -q tests/test_regression_free_plate_a1h3.py`

- Commit: `4c45339`
- Scope: zeta rewrite plan documentation
- Specs covered:
  - G39-G46 (plan documented)
- Verification:
  - Documentation-only

Notes:

- Prefer uv-first commands for repeatability: `uv run pytest -q`, `uv run black .`.
