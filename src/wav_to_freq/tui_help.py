# ==== FILE: src/wav_to_freq/tui_help.py ====
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Static, Markdown

HELP_MD = r"""
# wav-to-freq (alpha) — Help

This tool analyzes a **stereo WAV** recording of an impact test:

- **Hammer channel**: impulsive spikes (force input)
- **Accelerometer channel**: ring-down response (structure output)

The app:
1) Detects hits on the hammer channel
2) Extracts a response window around each hit
3) Estimates **fn** (dominant frequency) and **ζ** (damping ratio) from the response
4) Writes a preprocess + modal report (MD + PDF)

---

## Quick workflow

1. Set **Input directory** (app picks newest `.wav` inside)
2. Set **Output directory**
3. Choose a **Preset**
   - **Structures**: low frequency band, longer windows
   - **Xylophone**: higher band, longer ringing, more sensitive window tuning
4. Press **Run**

Open the generated PDF reports to judge quality.

---

## Basic knobs (most useful)

### Preset
Loads a coherent set of values.

### Frequency band: fmin_hz / fmax_hz
Constrains where the dominant peak is searched.
- Structures: e.g. 0.5–50 Hz
- Xylophone: e.g. 50–2000 Hz

### post_s (s)
How much response to keep after each hit (initial cut window).
If your beam rings a long time, increase this.

### ring_s (s)
How much of the response window is actually analyzed for modal extraction.
If damping is very low, increase this (often 2–5 s).

---

## Advanced knobs (when damping fit looks wrong)

### pre_s (s)
How much time to keep before the hit (baseline / context).

### min_separation_s (s)
Minimum spacing between hits to avoid double-detection.

### threshold_sigma
Hit detection sensitivity. Lower = more hits detected (and more false hits).

### settle_s (s)
Skips the first part of the response after impact (hammer contact/shock).

### transient_s / established_min_s (s)
Controls where the algorithm is allowed to start the “established” exponential decay fit.
If your envelope still shows beating early, increase these.

### established_r2_min
Minimum linearity (R²) required on log-envelope to accept a fit start.

### fit_max_s (s)
Maximum fit length after the chosen start.

### noise_tail_s / noise_mult
Used to estimate noise floor from the tail and stop the fit before noise dominates.
If you stop too early, reduce noise_mult or increase ring_s/post_s.
"""


class HelpScreen(ModalScreen[None]):
    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help_root {
        width: 90%;
        height: 90%;
        padding: 1 2;
        border: heavy $accent;
        background: $panel;
    }
    #help_title { padding-bottom: 1; }
    #help_scroll { height: 1fr; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help_root"):
            yield Static("Help — press Esc to close", id="help_title")
            with ScrollableContainer(id="help_scroll"):
                yield Markdown(HELP_MD)

    def action_close(self) -> None:
        # Correct way to close a ModalScreen
        self.dismiss(None)

