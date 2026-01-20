# ==== FILE: src/wav_to_freq/tui_app.py ====
from __future__ import annotations

import os
os.environ["MPLBACKEND"] = "Agg"

import json
import re
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import cast

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Select, Static

from wav_to_freq.domain.enums import StereoChannel
from wav_to_freq.pipeline import run_full_report
from wav_to_freq.tui_help import HelpScreen


# ----------------------------
# Persistence
# ----------------------------

def _default_config_path() -> Path:
    return Path.home() / ".config" / "wav_to_freq" / "ui.json"


@dataclass
class UiConfig:
    input_dir: str = ""
    output_dir: str = ""
    hammer_channel: str = "auto"  # auto|left|right
    preset: str = "structures"

    # basic
    fmin_hz: float = 0.5
    fmax_hz: float = 50.0
    post_s: float = 4.0
    ring_s: float = 3.0

    # advanced
    pre_s: float = 0.10
    min_separation_s: float = 0.80
    threshold_sigma: float = 6.0
    settle_s: float = 0.020

    transient_s: float = 0.50
    established_min_s: float = 1.50
    established_r2_min: float = 0.95
    fit_max_s: float = 2.00
    noise_tail_s: float = 0.50
    noise_mult: float = 3.0

    @classmethod
    def load(cls, path: Path) -> "UiConfig":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cfg = cls()
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
            return cfg
        except FileNotFoundError:
            return cls()
        except Exception:
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


PRESETS: dict[str, dict[str, float]] = {
    "structures": dict(
        fmin_hz=0.5,
        fmax_hz=50.0,
        pre_s=0.10,
        post_s=4.0,
        min_separation_s=0.80,
        threshold_sigma=6.0,
        settle_s=0.020,
        ring_s=3.0,
        transient_s=0.50,
        established_min_s=1.50,
        established_r2_min=0.95,
        fit_max_s=2.00,
        noise_tail_s=0.50,
        noise_mult=3.0,
    ),
    "xylophone": dict(
        fmin_hz=50.0,
        fmax_hz=2000.0,
        pre_s=0.05,
        post_s=6.0,
        min_separation_s=0.30,
        threshold_sigma=8.0,
        settle_s=0.010,
        ring_s=4.0,
        transient_s=0.30,
        established_min_s=1.20,
        established_r2_min=0.95,
        fit_max_s=3.00,
        noise_tail_s=0.30,
        noise_mult=3.0,
    ),
}


# ----------------------------
# WAV selection + folder naming
# ----------------------------

def find_latest_wav(input_dir: Path) -> Path | None:
    if not input_dir.exists() or not input_dir.is_dir():
        return None
    wavs = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.WAV"))
    if not wavs:
        return None
    return max(wavs, key=lambda p: p.stat().st_mtime)


def _sanitize_dirname(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\-\. ]+", "_", name)
    name = re.sub(r"\s+", " ", name)
    return name.replace(" ", "_") or "untitled"


def _make_unique_dir(base: Path) -> Path:
    if not base.exists():
        return base
    i = 2
    while True:
        candidate = base.parent / f"{base.name}_{i}"
        if not candidate.exists():
            return candidate
        i += 1


# ----------------------------
# App
# ----------------------------

class WavToFreqApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "help", "Help"),
        ("pagedown", "page_down", "Page down"),
        ("pageup", "page_up", "Page up"),
    ]

    CSS = """
    #main { height: 1fr; }
    .label { padding-top: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._cfg_path = _default_config_path()
        self._cfg = UiConfig.load(self._cfg_path)

    def compose(self) -> ComposeResult:
        yield Header()

        with VerticalScroll(id="main"):
            yield Static("Input directory (newest .wav is selected):", classes="label")
            yield Input(value=self._cfg.input_dir, placeholder="~/path/to/input_dir", id="input_dir")

            yield Static("Output directory (each run makes a subfolder):", classes="label")
            yield Input(value=self._cfg.output_dir, placeholder="~/path/to/output_dir", id="output_dir")

            yield Static("Hammer channel:", classes="label")
            yield Select(
                options=[("Auto-detect", "auto"), ("Left", "left"), ("Right", "right")],
                value=self._cfg.hammer_channel,
                id="hammer_channel",
            )

            yield Static("Preset:", classes="label")
            yield Select(
                options=[("Structures", "structures"), ("Xylophone", "xylophone")],
                value=self._cfg.preset,
                id="preset",
            )

            yield Static("Basic — frequency band (Hz):", classes="label")
            yield Static("fmin_hz")
            yield Input(value=str(self._cfg.fmin_hz), id="fmin_hz")
            yield Static("fmax_hz")
            yield Input(value=str(self._cfg.fmax_hz), id="fmax_hz")

            yield Static("Basic — window durations (s):", classes="label")
            yield Static("post_s (initial cut after hit)")
            yield Input(value=str(self._cfg.post_s), id="post_s")
            yield Static("ring_s (analyzed ringdown duration)")
            yield Input(value=str(self._cfg.ring_s), id="ring_s")

            yield Static("Advanced — hit detection / extraction:", classes="label")
            yield Static("pre_s")
            yield Input(value=str(self._cfg.pre_s), id="pre_s")
            yield Static("post_s (advanced override)")
            yield Input(value=str(self._cfg.post_s), id="post_s_adv")
            yield Static("min_separation_s")
            yield Input(value=str(self._cfg.min_separation_s), id="min_separation_s")
            yield Static("threshold_sigma")
            yield Input(value=str(self._cfg.threshold_sigma), id="threshold_sigma")

            yield Static("Advanced — modal time window:", classes="label")
            yield Static("settle_s")
            yield Input(value=str(self._cfg.settle_s), id="settle_s")
            yield Static("ring_s (advanced override)")
            yield Input(value=str(self._cfg.ring_s), id="ring_s_adv")

            yield Static("Advanced — established / damping fit:", classes="label")
            yield Static("transient_s")
            yield Input(value=str(self._cfg.transient_s), id="transient_s")
            yield Static("established_min_s")
            yield Input(value=str(self._cfg.established_min_s), id="established_min_s")
            yield Static("established_r2_min")
            yield Input(value=str(self._cfg.established_r2_min), id="established_r2_min")
            yield Static("fit_max_s")
            yield Input(value=str(self._cfg.fit_max_s), id="fit_max_s")
            yield Static("noise_tail_s")
            yield Input(value=str(self._cfg.noise_tail_s), id="noise_tail_s")
            yield Static("noise_mult")
            yield Input(value=str(self._cfg.noise_mult), id="noise_mult")

            yield Static("", classes="label")
            yield Button("Run (latest WAV)", id="run", variant="primary")
            yield Button("Help (h)", id="help_btn")
            yield Static("", id="status", markup=False)

        yield Footer()

    # ---- scrolling bindings (works even when Input has focus)
    def action_page_down(self) -> None:
        scroller = self.query_one("#main", VerticalScroll)
        if hasattr(scroller, "scroll_page_down"):
            scroller.scroll_page_down()  # type: ignore[attr-defined]
        else:
            scroller.scroll_relative(y=scroller.size.height - 2)

    def action_page_up(self) -> None:
        scroller = self.query_one("#main", VerticalScroll)
        if hasattr(scroller, "scroll_page_up"):
            scroller.scroll_page_up()  # type: ignore[attr-defined]
        else:
            scroller.scroll_relative(y=-(scroller.size.height - 2))

    # ---- help
    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def _set_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(msg)

    def _parse_float(self, widget_id: str, *, default: float) -> float:
        raw = self.query_one(f"#{widget_id}", Input).value.strip()
        try:
            return float(raw)
        except Exception:
            return float(default)

    def _parse_hammer_channel(self) -> StereoChannel:
        val = self.query_one("#hammer_channel", Select).value
        if val == "left":
            return StereoChannel.LEFT
        if val == "right":
            return StereoChannel.RIGHT
        return StereoChannel.UNKNOWN

    def _read_and_persist(self) -> tuple[Path, Path]:
        input_dir_raw = self.query_one("#input_dir", Input).value.strip()
        output_dir_raw = self.query_one("#output_dir", Input).value.strip()

        input_dir = Path(input_dir_raw).expanduser()
        output_dir = Path(output_dir_raw).expanduser()

        self._cfg.input_dir = input_dir_raw
        self._cfg.output_dir = output_dir_raw
        self._cfg.hammer_channel = cast(str, self.query_one("#hammer_channel", Select).value or "auto")
        self._cfg.preset = cast(str, self.query_one("#preset", Select).value or self._cfg.preset)

        # basic
        self._cfg.fmin_hz = self._parse_float("fmin_hz", default=self._cfg.fmin_hz)
        self._cfg.fmax_hz = self._parse_float("fmax_hz", default=self._cfg.fmax_hz)
        self._cfg.post_s = self._parse_float("post_s", default=self._cfg.post_s)
        self._cfg.ring_s = self._parse_float("ring_s", default=self._cfg.ring_s)

        # advanced overrides
        self._cfg.pre_s = self._parse_float("pre_s", default=self._cfg.pre_s)
        self._cfg.post_s = self._parse_float("post_s_adv", default=self._cfg.post_s)
        self._cfg.min_separation_s = self._parse_float("min_separation_s", default=self._cfg.min_separation_s)
        self._cfg.threshold_sigma = self._parse_float("threshold_sigma", default=self._cfg.threshold_sigma)
        self._cfg.settle_s = self._parse_float("settle_s", default=self._cfg.settle_s)
        self._cfg.ring_s = self._parse_float("ring_s_adv", default=self._cfg.ring_s)

        self._cfg.transient_s = self._parse_float("transient_s", default=self._cfg.transient_s)
        self._cfg.established_min_s = self._parse_float("established_min_s", default=self._cfg.established_min_s)
        self._cfg.established_r2_min = self._parse_float("established_r2_min", default=self._cfg.established_r2_min)
        self._cfg.fit_max_s = self._parse_float("fit_max_s", default=self._cfg.fit_max_s)
        self._cfg.noise_tail_s = self._parse_float("noise_tail_s", default=self._cfg.noise_tail_s)
        self._cfg.noise_mult = self._parse_float("noise_mult", default=self._cfg.noise_mult)

        self._cfg.save(self._cfg_path)
        return input_dir, output_dir

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "preset":
            return

        preset = cast(str, event.value)
        if preset not in PRESETS:
            return

        for k, v in PRESETS[preset].items():
            setattr(self._cfg, k, float(v))
        self._cfg.preset = preset
        self._cfg.save(self._cfg_path)

        # Update fields (best-effort)
        def set_input(wid: str, val: float) -> None:
            try:
                self.query_one(f"#{wid}", Input).value = str(val)
            except Exception:
                pass

        set_input("fmin_hz", self._cfg.fmin_hz)
        set_input("fmax_hz", self._cfg.fmax_hz)
        set_input("post_s", self._cfg.post_s)
        set_input("post_s_adv", self._cfg.post_s)
        set_input("ring_s", self._cfg.ring_s)
        set_input("ring_s_adv", self._cfg.ring_s)
        set_input("pre_s", self._cfg.pre_s)
        set_input("min_separation_s", self._cfg.min_separation_s)
        set_input("threshold_sigma", self._cfg.threshold_sigma)
        set_input("settle_s", self._cfg.settle_s)
        set_input("transient_s", self._cfg.transient_s)
        set_input("established_min_s", self._cfg.established_min_s)
        set_input("established_r2_min", self._cfg.established_r2_min)
        set_input("fit_max_s", self._cfg.fit_max_s)
        set_input("noise_tail_s", self._cfg.noise_tail_s)
        set_input("noise_mult", self._cfg.noise_mult)

        self._set_status(f"Preset applied: {preset}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help_btn":
            self.action_help()
            return

        if event.button.id != "run":
            return

        input_dir, output_dir = self._read_and_persist()

        if not input_dir.exists() or not input_dir.is_dir():
            self._set_status("❌ Input directory is invalid.")
            return

        output_dir.mkdir(parents=True, exist_ok=True)

        wav_path = find_latest_wav(input_dir)
        if wav_path is None:
            self._set_status("❌ No .wav files found in input directory.")
            return

        run_dir = _make_unique_dir(output_dir / _sanitize_dirname(wav_path.stem))
        run_dir.mkdir(parents=True, exist_ok=True)

        self._set_status(f"Running…\nSelected: {wav_path}\nRun folder: {run_dir}\n")
        self.run_worker(lambda: self._pipeline_worker(wav_path, run_dir), thread=True)

    def _pipeline_worker(self, wav_path: Path, run_dir: Path) -> None:
        try:
            artifacts = run_full_report(
                wav_path,
                out_dir=run_dir,
                hammer_channel=self._parse_hammer_channel(),

                pre_s=self._cfg.pre_s,
                post_s=self._cfg.post_s,
                min_separation_s=self._cfg.min_separation_s,
                threshold_sigma=self._cfg.threshold_sigma,

                fmin_hz=self._cfg.fmin_hz,
                fmax_hz=self._cfg.fmax_hz,

                settle_s=self._cfg.settle_s,
                ring_s=self._cfg.ring_s,

                transient_s=self._cfg.transient_s,
                established_min_s=self._cfg.established_min_s,
                established_r2_min=self._cfg.established_r2_min,
                fit_max_s=self._cfg.fit_max_s,
                noise_tail_s=self._cfg.noise_tail_s,
                noise_mult=self._cfg.noise_mult,

                title_preprocess="WAV preprocessing report",
                title_modal="Modal report",
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"❌ Failed: {exc!r}")
            return

        dest_wav = run_dir / wav_path.name
        if dest_wav.exists():
            dest_wav = run_dir / f"{wav_path.stem}__treated{wav_path.suffix}"

        try:
            shutil.move(str(wav_path), str(dest_wav))
        except Exception as exc:
            self.call_from_thread(
                self._set_status,
                "⚠️ Analysis succeeded but moving WAV failed.\n"
                f"Reason: {exc!r}\n"
                f"Run folder: {run_dir}\n"
                f"WAV remains at: {wav_path}\n"
                f"Modal CSV: {artifacts.modal.report_csv}\n",
            )
            return

        msg = (
            "✅ Done\n"
            f"Run folder:    {run_dir}\n"
            f"Moved WAV:     {dest_wav}\n\n"
            f"Preprocess MD: {artifacts.preprocess.report_md}\n"
            f"Modal MD:      {artifacts.modal.report_md}\n"
            f"Modal CSV:     {artifacts.modal.report_csv}\n"
        )
        self.call_from_thread(self._set_status, msg)


def main() -> None:
    WavToFreqApp().run()


if __name__ == "__main__":
    main()

