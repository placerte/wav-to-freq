from __future__ import annotations
import os
os.environ["MPLBACKEND"] = "Agg"

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, Input, Static

from wav_to_freq.pipeline import run_full_report


# ----------------------------
# Persistence (super simple)
# ----------------------------

def _default_config_path() -> Path:
    return Path.home() / ".config" / "wav_to_freq" / "ui.json"


@dataclass
class UiConfig:
    input_dir: str = ""
    output_dir: str = ""

    @classmethod
    def load(cls, path: Path) -> "UiConfig":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                input_dir=str(data.get("input_dir", "")),
                output_dir=str(data.get("output_dir", "")),
            )
        except FileNotFoundError:
            return cls()
        except Exception:
            # if config is corrupt, ignore it rather than crashing the app
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
    name = re.sub(r"[^\w\-\. ]+", "_", name)  # replace weird chars
    name = re.sub(r"\s+", " ", name)          # collapse spaces
    name = name.replace(" ", "_")
    return name or "untitled"


def _make_unique_dir(base: Path) -> Path:
    if not base.exists():
        return base
    i = 2
    while True:
        candidate = base.with_name(f"{base.name}__{i}")
        if not candidate.exists():
            return candidate
        i += 1


# ----------------------------
# Textual app
# ----------------------------

class WavToFreqApp(App):
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self._cfg_path = _default_config_path()
        self._cfg = UiConfig.load(self._cfg_path)

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="root"):
            yield Static("Input directory (we pick the newest .wav inside):", classes="label")
            yield Input(value=self._cfg.input_dir, placeholder="~/path/to/input_dir", id="input_dir")

            yield Static("Output directory (each run goes in a subfolder):", classes="label")
            yield Input(value=self._cfg.output_dir, placeholder="~/path/to/output_dir", id="output_dir")

            yield Button("Run (latest WAV)", id="run", variant="primary")
            yield Static("", id="status", markup=False)

        yield Footer()

    def on_mount(self) -> None:
        if not self._cfg.input_dir or not self._cfg.output_dir:
            self._set_status("Set input/output directories, then Run.")

    def _set_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(msg)

    def _read_dirs_and_persist(self) -> tuple[Path, Path]:
        input_dir = Path(self.query_one("#input_dir", Input).value.strip()).expanduser()
        output_dir = Path(self.query_one("#output_dir", Input).value.strip()).expanduser()

        # Persist exactly what the user typed (so ~ remains ~ if they want),
        # but use expanded Paths for actual IO.
        self._cfg.input_dir = self.query_one("#input_dir", Input).value.strip()
        self._cfg.output_dir = self.query_one("#output_dir", Input).value.strip()
        self._cfg.save(self._cfg_path)

        return input_dir, output_dir

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "run":
            return

        input_dir, output_dir = self._read_dirs_and_persist()

        if not input_dir.exists() or not input_dir.is_dir():
            self._set_status("❌ Input directory is invalid.")
            return

        output_dir.mkdir(parents=True, exist_ok=True)

        wav_path = find_latest_wav(input_dir)
        if wav_path is None:
            self._set_status("❌ No .wav files found in input directory.")
            return

        sub_name = _sanitize_dirname(wav_path.stem)
        run_dir = _make_unique_dir(output_dir / sub_name)
        run_dir.mkdir(parents=True, exist_ok=True)

        self._set_status(
            "Running…\n"
            f"Selected:   {wav_path}\n"
            f"Run folder: {run_dir}\n"
        )

        # IMPORTANT: run only once, into run_dir
        self.run_worker(lambda: self._pipeline_worker(wav_path, run_dir), thread=True)

    def _pipeline_worker(self, wav_path: Path, run_dir: Path) -> None:
        try:
            artifacts = run_full_report(
                wav_path,
                out_dir=run_dir,
                fmin_hz=1.0,
                fmax_hz=2000.0,
                title_preprocess="WAV preprocessing report",
                title_modal="Modal report",
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"❌ Failed: {exc!r}")
            return

        # Move treated WAV into the run folder (keep original name)
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
                f"Modal CSV: {artifacts.modal.report_csv}\n"
            )
            return

        msg = (
            "✅ Done\n"
            f"Run folder:   {run_dir}\n"
            f"Moved WAV:    {dest_wav}\n\n"
            f"Preprocess MD: {artifacts.preprocess.report_md}\n"
            f"Modal MD:      {artifacts.modal.report_md}\n"
            f"Modal CSV:     {artifacts.modal.report_csv}\n"
        )
        self.call_from_thread(self._set_status, msg)

def main():
    WavToFreqApp().run()

if __name__ == "__main__":
    main()


