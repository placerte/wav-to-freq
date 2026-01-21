# AGENTS.md (wav-to-freq)

This repo is an internal engineering tool. Code should be readable and navigable
by a mechanical engineer (simple Python, small files, explicit data flow).

Primary docs:

- Spec (normative): `docs/specs.md`
- Decision log: `docs/specs_clarifications.md`
- Architecture plan: `docs/implementation.md`
- V1 must-ship tracking: `docs/traceability_v1.md`
- Legacy reference during rewrite: `src/legacy/`

Cursor/Copilot rules:

- `.cursor/rules/`: not present
- `.cursorrules`: not present
- `.github/copilot-instructions.md`: not present

---

## 1) Build / Lint / Typecheck / Test Commands

Python version:

- Requires Python >= 3.12 (see `pyproject.toml`).

Environment setup (preferred: uv)

This repo includes `uv.lock`, so uv is the simplest way to get a matching env.

- Create/sync env:
  - `uv sync`
- Install dev tools:
  - `uv sync --group dev`

Environment setup (fallback: venv + pip)

- `python -m venv .venv`
- `source .venv/bin/activate`
- `pip install -e .`
- Dev tools (minimal):
  - `pip install black`
  - (optional) `pip install pyright pytest`

Run the app (TUI)

- Installed script:
  - `wav-to-freq`
- Without installing:
  - `python -m wav_to_freq.tui_app`

PDF export dependencies

- Markdown reports work by default.
- PDF export prefers `pandoc` + LaTeX; otherwise falls back to WeasyPrint.

Debian/Ubuntu example:

- `sudo apt-get install -y pandoc texlive-latex-base texlive-latex-recommended texlive-latex-extra`

Format (Black)

- `black .`

Static typecheck (Pyright)

Note: pyright is configured in `pyproject.toml` under `[tool.pyright]` but is not
pinned as a dependency. Install it if needed.

- `pyright`

Complexity (optional)

`radon` is listed in dev deps.

- `radon cc -s -a src/wav_to_freq`

Build binary (optional)

There is a PyInstaller spec file.

- `pyinstaller wav-to-freq.spec`

Tests

- Currently there is no `tests/` directory checked in.
- Once tests exist, standard commands should be:
  - `pytest`
  - `pytest -q`

Run a single test (pytest)

- By node id:
  - `pytest -q path/to/test_file.py::test_name`
- By keyword:
  - `pytest -q -k "noise_floor"`

---

## 2) Code Style Guidelines

### 2.1 Philosophy

- Prefer plain Python (no MVVM/DDD frameworks).
- Prefer small files (~100-250 lines) and small functions that do one thing.
- Prefer explicit data flow over clever abstractions.
- Keep core computation deterministic for a given input + config (see specs L68).

### 2.2 Imports

Keep imports grouped in this order (blank line between groups):

1) `from __future__ import annotations` (first line when used)
2) standard library
3) third-party
4) local `wav_to_freq.*`

Avoid:

- wildcard imports
- deeply nested import cycles

### 2.3 Formatting

- Use Black for formatting.
- If a function becomes hard to read, split it into helpers (prefer refactor
  over comments).
- Keep docstrings short and practical (what/why, not textbook).

### 2.4 Types

- Use Python 3.12 typing (`X | None`, `list[str]`, etc.).
- Prefer adding `from __future__ import annotations` in new modules.
- Use dataclasses for structured data that crosses module boundaries.

For numpy arrays:

- Public dataclasses: `numpy.ndarray` is acceptable.
- Analysis internals: consider `numpy.typing.NDArray[np.float64]` for clarity.

Pyright config notes:

- `pyproject.toml` sets:
  - `venvPath = "."`, `venv = ".venv"`, `extraPaths = ["src"]`

### 2.5 Naming conventions

- Functions: `snake_case` with verbs (compute/estimate/extract/write)
- Classes/dataclasses: `PascalCase` with nouns (`HitWindow`, `PeakCandidate`)
- Constants: `UPPER_SNAKE_CASE`
- Prefer descriptive names over short names.

Examples:

- good: `compute_noise_floor_percentile`
- avoid: `calc_nf`

### 2.6 Error handling and validation

- Invalid input or impossible states:
  - `ValueError` for bad parameter values
  - `FileNotFoundError` for missing files
- Analysis code should prefer returning structured "not computed" results rather
  than raising, when a failure is an expected outcome (ties into spec statuses).
- UI/reporting code may catch exceptions to provide a fallback (example: PDF
  export fallback), but must keep failure modes visible to the user (do not
  silently ignore).

### 2.7 Determinism and reproducibility

- No randomness.
- Any heuristic must be deterministic and fully governed by logged config.
- Outputs should log key parameters (see specs L66/L67).

### 2.8 Where code should live (separation of concerns)

- `wav_to_freq/io/*`: WAV reading, channel selection, hit detection/window extraction
- `wav_to_freq/analysis/*`: math/estimation/diagnostics (should be testable)
- `wav_to_freq/reporting/*`: plots and writers (md/pdf/csv/json)
- `wav_to_freq/app/*` or TUI files: UI only (no heavy math)

### 2.9 Rewrite workflow

- Legacy code stays available under `src/legacy/` for reference.
- Rewrite incrementally, module-by-module, following `docs/implementation.md`.
- Keep `docs/traceability_v1.md` updated for v1 must-ship requirements.
