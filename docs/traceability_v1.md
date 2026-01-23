# V1 Traceability

Tracks only v1 "must ship" requirements.

- Requirement text lives in `docs/specs.md`.
- Decisions/rationale live in `docs/specs_clarifications.md`.
- Evidence should prefer tests once they exist; until then, code references are acceptable.

Status values:

- `todo`: not implemented
- `partial`: partially implemented / missing tests / missing outputs
- `done`: implemented with evidence

| req_id | short_name | status | evidence | notes |
|---|---|---|---|---|
| A1 | Stereo WAV only | done | `src/wav_to_freq/io/wav_reader.py` | Enforced by channel count check. |
| A2 | Channel roles set in TUI | partial | `src/wav_to_freq/tui_app.py` | TUI supports selection, but defaults allow "auto" without explicit confirmation. |
| A3 | Refuse run without roles | partial | `src/wav_to_freq/tui_app.py` | Needs explicit "must choose" gating in UI to satisfy spec intent. |
| A4 | Persist channel mapping in outputs | partial | `src/wav_to_freq/reporting/sections/preprocess.py` | Hammer channel shown; need full config echo (L66) and explicit "role" language. |
| B5 | Hits detected from hammer only | done | `src/wav_to_freq/io/hit_detection.py` | `prepare_hits()` uses hammer channel for detection. |
| B7 | Min hit separation configurable | done | `src/wav_to_freq/io/hit_detection.py` | `min_separation_s` default 0.30 and configurable. |
| (check) | Regression: free srl2 1.wav | partial | `tests/test_regression_free_srl2_1.py` | Asserts 10 hits and primary fn=150.732 Hz for a known file. |
| (check) | Regression: free srl2 2-4 | partial | `tests/test_regression_free_srl2_2.py` | Adds global peaks and hit counts for SRL2 variants. |
| (check) | Regression: free srp 1-4 | partial | `tests/test_regression_free_srp_1.py` | Baseline checks for SRP rail samples. |
| (check) | Regression: free plate A1H3/A2H4/A3H1 | partial | `tests/test_regression_free_plate_a1h3.py` | Validates peak detection counts for plate samples. |
| C13 | Default post-hit duration 1.5s | partial | `src/wav_to_freq/pipeline.py` | Pipeline default is 1.50; TUI preset defaults differ. |
| C16 | Hybrid full vs established fit | done | `src/wav_to_freq/analysis/estimators/td_envelope.py` | TD estimator produces full + established fits per peak (reported as separate methods). |
| D17 | Response DC removal, no global HP | done | `src/wav_to_freq/analysis/modal.py` | Mean removal is applied to response segment. |
| D19 | Butterworth order-4 band-pass + filtfilt | done | `src/wav_to_freq/analysis/modal.py` | `_bandpass()` uses butter(4)+filtfilt. |
| D20 | 0.6x-1.4x band rule + guardrails | partial | `src/wav_to_freq/analysis/modal.py` | 0.6/1.4 implemented; adjacent-peak guardrails + logging not implemented. |
| D21 | No taper; use transient_s | partial | `src/wav_to_freq/analysis/modal.py` | `transient_s` exists; missing explicit NOT_COMPUTED on filtfilt padding failure and logging. |
| E24 | Global + per-hit PSD peak handling | done | `src/wav_to_freq/analysis/estimators/run.py` | Global list + per-hit refinement are used to form the per-hit peak list used for estimation. |
| E25 | Welch PSD w/ logged configurable params | partial | `src/wav_to_freq/dsp/psd.py` | Welch wrapper is used for estimation/reporting; still missing full config echo/logging in outputs (L66). |
| E26 | PSD noise floor percentile (q=60) | done | `src/wav_to_freq/analysis/peaks/noise_floor.py` | Percentile noise floor implemented + unit tests. |
| E27 | Peak validity via peak_snr_db + cap 5 | partial | `src/wav_to_freq/analysis/peaks/psd_peaks.py` | SNR gating + cap implemented; not yet integrated into reports. |
| E28 | Peak de-duplication/merging rule | done | `src/wav_to_freq/analysis/peaks/merge.py` | Merge rule implemented + unit tests. |
| E29 | Keep close peaks + coupled flags | done | `src/wav_to_freq/analysis/peaks/merge.py` | Coupled-flagging implemented + unit tests (keeps peaks). |
| F31 | Diagnostics numeric + flags | done | `src/wav_to_freq/analysis/estimators/pipeline.py` | Estimator pipeline attaches numeric diagnostics + reason-code flags; modal report renders them per method. |
| F34 | Beating score + BEATING_DETECTED | done | `src/wav_to_freq/analysis/diagnostics/beating.py` | Implemented + `tests/test_diagnostics_flags.py`. |
| F35 | Envelope monotonicity metric + flag | done | `src/wav_to_freq/analysis/diagnostics/monotonicity.py` | Implemented + `tests/test_diagnostics_flags.py`. |
| F36 | Instantaneous frequency drift | done | `src/wav_to_freq/analysis/diagnostics/inst_freq.py` | Implemented + `tests/test_diagnostics_flags.py`. |
| F37 | Filter ringing risk q_factor | done | `src/wav_to_freq/analysis/diagnostics/filter_risk.py` | Implemented + unit test coverage. |
| G39 | TD Hilbert envelope log-fit estimator | done | `src/wav_to_freq/analysis/estimators/td_envelope.py` | Implemented and used for per-peak damping (full + established). |
| G42 | Half-power bandwidth estimator | done | `src/wav_to_freq/analysis/estimators/pipeline.py` | Implemented and emitted as `FD_HALF_POWER` estimates (with NOT_COMPUTED on failure). |
| G44 | Energy decay proxy (envelope_sq) | done | `src/wav_to_freq/analysis/estimators/pipeline.py` | Implemented and emitted as `ENERGY_ENVELOPE_SQ` estimates. |
| G46 | EFFECTIVE_DAMPING_ONLY labeling | done | `src/wav_to_freq/analysis/estimators/energy_decay.py` | Energy estimates always carry `EFFECTIVE_DAMPING_ONLY` and it is rendered in the modal report. |
| H47 | Deterministic status mapping | done | `src/wav_to_freq/analysis/status/mapping.py` | All estimator outputs are passed through deterministic `assess_estimate()`. |
| H50 | NOT_COMPUTED status exists | done | `src/wav_to_freq/domain/status.py` | `EstimateStatus.NOT_COMPUTED` introduced as v1 status. |
| H51 | Show rejected values; exclude from aggregates | partial | `src/wav_to_freq/reporting/writers/modal.py` | Rejects are displayed; need explicit OK/WARNING/REJECTED/NOT_COMPUTED and default exclusion rules. |
| I53 | Best guess per (hit, fi) | todo |  | Not implemented (single `fn`/`zeta` per hit today). |
| J56 | Group peaks across hits; stable mode_id | todo |  | Not implemented. |
| K61 | Preprocess report: md+pdf + field checks | partial | `src/wav_to_freq/reporting/writers/preprocess.py` | Report exists (md/pdf optional); needs hit timestamps + go/no-go diagnostics per spec. |
| K63 | Per-hit+per-fi plots (cap 5 peaks) | partial | `src/wav_to_freq/reporting/sections/modal.py` | Per-peak filtered plots + per-method diagnostic plots exist; hit-level PSD peak annotations still need to use the estimator peak list. |
| K65 | Stable output directory structure | partial | `src/wav_to_freq/reporting/writers/modal.py` | Some structure exists; needs to align to K65 contract exactly. |
| L66 | Echo full analysis config in outputs | todo |  | Not implemented. |
| L67 | Stamp version/git hash in outputs | todo |  | Not implemented. |
| M71 | Clipping detected + flagged | todo |  | Not implemented. |
| N74 | Stable analysis_results.json schema | todo |  | Not implemented. |

Notes:

- This list is intentionally small; not all spec IDs are tracked here.
- Add evidence links as implementations land (tests preferred).
