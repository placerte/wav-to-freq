# Modal report layout

In here I explain the modal report desired layout the sections below are formated in markdown and is intended to show structure. *italics* will indicate instructions not just pure template or text.

# Modal Summary

With the summary and table -> *OK for now. keep it as is and move on*

# Hits

## H001

- Time Domain (TD) raw response plot. *Keep it similar to the one already used right now, or do minimal changes*
- Fequency domain (FD) response plot. *Again keep it similar to the one already used right now, only make sure that identified peaks are the one processed by the typical hit processor and not some "sub plot processor" in the plot methods (there might be this artifact in the code)

### Peak 1 - f_1 = xx Hz

- plot of filtered raw response (TD) filtered for f_1. *keep the plot similar to what is already done right now*

#### ζ_TD_1 = x.xxx

*Here I have less experience. Please provide all the relevant information AND plots to identify, computed values, computed log curve fit. I should be able to confirm visually "yep this value seems right or no there is some bad data or whatever. I'd like to see reasons for a good fit and also reasons for a bad fit"*

#### ζ_FD_1 = x.xxx

*Same as ζ_TD_1. I don't have much experience with this so please provide all relevant information and visualization for ζ_FD_1*

#### ζ_E_1 = x.xxx

*Same as ζ_TD_1. I don't have much experience with this so please provide all relevant information and visualization for ζ_E_1*

### Peak 2 - f_2 = xx Hz

*Same structure as previous peak (peak 1) of parent hit (H001)*

#### ζ_TD_2 = x.xxx

#### ζ_FD_2 = x.xxx

#### ζ_E_2 = x.xxx

...
*loop through all peaks of hit H001 until*

### Peak m - f_m = xx Hz

*Same structure as previous peak (peak m-1) of parent hit (H001)*

#### ζ_TD_2 = x.xxx

#### ζ_FD_2 = x.xxx

#### ζ_E_2 = x.xxx

*then to the next hit*

## H002

### Peak 1 - f_1 = xx Hz

#### ζ_TD_1 = x.xxx

#### ζ_FD_1 = x.xxx

#### ζ_E_1 = x.xxx

### Peak 2 - f_2 = xx Hz

#### ζ_TD_2 = x.xxx

#### ζ_FD_2 = x.xxx

#### ζ_E_2 = x.xxx

...

### Peak m - f_m = xx Hz

*Same structure as previous peak (peak m-1) of parent hit (H002)*

#### ζ_TD_2 = x.xxx

#### ζ_FD_2 = x.xxx

#### ζ_E_2 = x.xxx

*And do this for all hits in the report until H00n_hits. To simplify the desired hiearchy is HIT > contains > peaks (f_i) > contains > zetas (\zeta_foo) or methods to obtain zetas

---

# Implementation status (2026-01-23)

This layout is now implemented in the generated modal report:

- Hierarchy: `Hits` -> `H###` -> `Peak i - f_i = ...` -> `zeta_TD_i / zeta_FD_i / zeta_E_i`.
- Each peak includes a filtered TD response plot for `f_i`.
- Each method subsection includes status + flags/reasons + a diagnostic plot intended to make the computed value auditable.

Known gaps / follow-ups:

- The per-hit frequency-domain response plot should annotate the exact peak list used by the estimator pipeline (avoid any separate peak-picking logic inside the plotting helper).
- TD/Energy diagnostic plots should ideally use the exact fit-window indices used during estimation (currently inferred from durations in diagnostics).
