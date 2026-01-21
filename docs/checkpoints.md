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

- Commit: `8e01327`
- Scope: v1 domain model foundation + initial unit tests
- Specs covered:
  - H50 (NOT_COMPUTED status introduced)
  - H48 (reason-code hard/soft sets introduced)
  - Supporting types for E/K/N outputs (`ReasonCode`, `EstimateStatus`, `EstimateResult`)
- Verification:
  - `python3 -m pytest -q` (passed)
- Notes:
  - Black formatting not run in this environment (module not available on system python); run `uv run black src tests` in the project env.
