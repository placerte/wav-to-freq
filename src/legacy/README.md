# Legacy Code (v0 reference)

This directory holds legacy code as we rewrite `wav-to-freq` against the v1 specs.

Intent:

- Keep the current, working implementation available for reference.
- Migrate module-by-module into the new v1 architecture.
- Avoid "big bang" refactors.

Workflow rule:

- When we rewrite a module, we move the previous implementation into this directory (keeping filenames and a short note about what it used to do).
- New code lives under `src/wav_to_freq/`.

Notes:

- This is an internal tool; readability for a mechanical engineer is prioritized.
- Prefer small files and small functions with good names.
