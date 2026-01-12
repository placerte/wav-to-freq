# Method notes (wav-to-freq)

## Context

This project targets practical field modal surveys using:
- an instrumented impact hammer
- an accelerometer
- a two-channel WAV recording

Current focus: linear behavior and dominant mode extraction.

## Signal model

An impulse-like input excites structural modes.
After the impact, the response can be approximated by damped sinusoids.
For lightly damped systems, the decay envelope is approximately exponential.

## Estimated quantities

Per impact:
- natural frequency (fn)
- damping ratio (ζ)
- fit quality metrics (used for hit rejection)

## Practical considerations

- Early transient behavior can bias damping estimates.
- Multiple hits provide internal consistency checks.
- Robust, repeatable results are prioritized over theoretical completeness.
