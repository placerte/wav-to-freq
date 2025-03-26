from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D
from file_handler import WavSampleFile, save_all_data
from computing import DampingEnvelopeCurveFitter, compute_fft_from_wav_file

import numpy as np
import matplotlib.pyplot as plt

import matplotlib.gridspec as gridspec
from matplotlib.table import Table
from matplotlib.axes import Axes
from matplotlib.text import Annotation
from matplotlib.backend_bases import MouseButton, MouseEvent, CloseEvent
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import Size 

from typing import List, Optional

import tkinter as tk
from tkinter import messagebox


class Plotter:

    wav_file: WavSampleFile
    curve_fitter: DampingEnvelopeCurveFitter

    time_data: np.ndarray
    amplitude_data: np.ndarray
    freq_data: np.ndarray
    magnitude_data: np.ndarray
    n_samples: int

    time_scatter_data: PathCollection
    frequency_scatter_data: PathCollection | None
    frequency_scatter_annotations: list[Annotation]

    time_domain_plot: Axes
    frequency_domain_plot: Axes
    file_info_plot: Axes
    file_info_table: Table
    fitted_curve_info_plot: Axes
    fitted_curve_info_table: Table
    fitted_curve_line: Optional[Line2D]

    figure: Figure
    figure_grid_spec: gridspec.GridSpec

    def __init__(self, wav_sample_file: WavSampleFile) -> None:
        self.wav_file = wav_sample_file
        self.curve_fitter = DampingEnvelopeCurveFitter()
        self.fitted_curve_line = None
        self.frequency_scatter_data = None
        self.frequency_scatter_annotations = []
        self.extract_data_from_wav_file()
        self.build_figure_layout()
        self.generate_initial_plots()

    @property
    def time_scatter_values(self) -> np.ndarray:
        """Ensures that the scatter points are sorted in ascending order."""
        if self.time_scatter_data is None:
            return np.array([])

        offsets = np.asarray(self.time_scatter_data.get_offsets())
        if offsets.size == 0:
            return np.array([])

        sorted_indices = np.argsort(offsets[:, 0])  # Sort by time values
        return offsets[sorted_indices, 0]  # Return sorted time values

    @property
    def amplitude_scatter_values(self) -> np.ndarray:
        """Returns amplitude values sorted in the same order as time_scatter_values."""
        if self.time_scatter_data is None:
            return np.array([])  # Return empty array if no data

        offsets = np.asarray(self.time_scatter_data.get_offsets())
        if offsets.size == 0:
            return np.array([])

        sorted_indices = np.argsort(offsets[:, 0])  # Sort by time values
        return offsets[sorted_indices, 1]  # Return amplitudes sorted in time order

    def extract_data_from_wav_file(self):
        (
            self.time_data,
            self.amplitude_data,
            self.freq_data,
            self.magnitude_data,
            self.n_samples,
        ) = compute_fft_from_wav_file(self.wav_file.filepath)

    def build_figure_layout(self):
        # Set up the figure and layout
        self.figure = plt.figure(figsize=(12, 6))
        self.figure_grid_spec = gridspec.GridSpec(nrows=2, ncols=2, width_ratios=[6, 3])

        # Place elements
        self.time_domain_plot = self.figure.add_subplot(self.figure_grid_spec[0, 0])
        self.frequency_domain_plot = self.figure.add_subplot(
            self.figure_grid_spec[1, 0]
        )
        self.file_info_plot = self.figure.add_subplot(self.figure_grid_spec[1, 1])
        self.fitted_curve_info_plot = self.figure.add_subplot(
            self.figure_grid_spec[0, 1]
        )

        # Register Click Event
        self.figure.canvas.mpl_connect("button_press_event", self.on_plot_click)
        self.figure.canvas.mpl_connect(
            "close_event", lambda event: self.on_close(event)
        )

        plt.tight_layout()

    def show(self):
        plt.show()

    def generate_initial_plots(self):
        self.plot_time_domain()
        self.plot_frequency_domain()
        self.plot_file_info_table()
        self.plot_fitted_curve_info_table()

    def plot_time_domain(self):
        """Plots the time_data-domain representation."""

        ###TESTING PLOTTING ON A LOG SCALE
        #a_offset: float = float(np.min(self.amplitude_data))-1
        #self.time_domain_plot.plot(self.time_data, np.log(self.amplitude_data-a_offset), label="TEST LOG")
        ### END OF TESTING

        self.time_domain_plot.plot(self.time_data, self.amplitude_data, label="Waveform response")
        self.time_domain_plot.set_title(
            f"Time Domain Representation - {self.wav_file.friendly_identifier}"
        )
        self.time_domain_plot.set_xlabel("Time (seconds)")
        self.time_domain_plot.set_ylabel("Amplitude")
        self.time_domain_plot.grid()
        self.time_domain_plot.legend()
        # Initialize scatter plot with no points
        self.time_scatter_data = self.time_domain_plot.scatter([], [], color="red", label="Considered peaks")

    def plot_frequency_domain(self):
        """Plots the frequency-domain representation."""
        #self.frequency_domain_plot.plot(
        #    self.freq_data[: self.n_samples // 2],
        #    np.abs(self.magnitude_data[: self.n_samples // 2]) / self.n_samples,
        #    label="Frequency spectrum of response"
        #)

        self.frequency_domain_plot.plot(
            self.freq_data,
            np.abs(self.magnitude_data),
            label="Frequency spectrum of response"
        )
        self.frequency_domain_plot.set_title(
            f"Frequency Domain Representation - {self.wav_file.friendly_identifier}"
        )
        self.frequency_domain_plot.set_xlabel("Frequency (Hz)")
        self.frequency_domain_plot.set_ylabel("Magnitude")
        self.frequency_domain_plot.grid()
        # Initialize scatter plot with no points
        self.frequency_scatter_data = self.frequency_domain_plot.scatter([], [], color="red", label="Modal natural frequencies")
        self.frequency_scatter_annotations = []
    # TODO: move to filehandler
    def get_file_info(self) -> list[list[str]]:

        return [
            ["File Properties", ""],
            ["File", self.wav_file.filename_with_extension],
            ["Sample Rate", f"{self.wav_file.sample_rate}Hz"],
            ["Duration", f"{self.wav_file.duration:.3f}s"],
            ["Channel(s)", str(self.wav_file.channel_count)],
            [
                "Creation Datetime",
                str(self.wav_file.creation_datetime.replace(microsecond=0)),
            ],
            [
                "Modification Datetime",
                str(self.wav_file.modification_datetime.replace(microsecond=0)),
            ],
        ]

    def promote_first_table_row_to_title(self, table: Table):
        table[0, 0].set_linewidth(0)
        table[0, 1].set_linewidth(0)
        table[0, 0].get_text().set_fontweight("bold")
        table[0, 0].get_text().set_horizontalalignment("left")
        table.auto_set_font_size(False)
        table.set_fontsize(10)

    def plot_file_info_table(self):

        self.file_info_plot.axis("off")
        # Populate Table
        self.file_info_table = self.file_info_plot.table(
            cellText=self.get_file_info(),
            colLabels=None,
            loc="center",
            cellLoc="center",
        )
        # "Pomote" first row to "tilte"
        self.promote_first_table_row_to_title(self.file_info_table)

    def get_fitted_curve_info(self) -> list[list[str]]:

        if self.curve_fitter.solved_parameters is None:

            return [
                ["Fitted Curve", ""],
                ["No data yet.", "Add points to fit the curve"],
                ["", ""],
                ["", ""],
                ["", ""],
                ["", ""],
                ["", ""],
                ["", ""],
                ["", ""],
            ]

        return [
            ["Fitted Curve", ""],
            [
                "Natural Frequency, ƒ_n (ω_n)",
                f"{self.curve_fitter.natural_freqency_f_n:.1f}Hz ({self.curve_fitter.natural_frequency_omega_n:.1f}rad/s)",
            ],
            [
                "Damped Natural Frequency, ƒ_d (ω_d)",
                f"{self.curve_fitter.damped_natural_frequency_f_d:0.1f}Hz ({self.curve_fitter.damped_natural_frequency_omega_d:.1f}rad/s)",
            ],
            [
                "Damping Ratio, ζ",
                f"{100*self.curve_fitter.get_damping_ratio_zeta():.2f}%",
            ],
            [
                "Number of considered peaks",
                f"{len(self.curve_fitter.time_scatter_values)}",
            ],
            [
                "Initial Amplitude, A_0",
                f"{int(self.curve_fitter.solved_parameters.a_0)}",
            ],
            [
                "Applitude offset, A_offset",
                f"{int(self.curve_fitter.solved_parameters.a_offset)}",
            ],
            [
                "Time offset, t_offset",
                f"{self.curve_fitter.solved_parameters.t_offset:0.3f}s",
            ],
            [
                "Coefficient of Determination, R²",
                f"{self.curve_fitter.get_coefficient_of_determination():.3f}",
            ],
        ]

    def plot_fitted_curve_info_table(self):

        self.fitted_curve_info_plot.axis("off")
        # Populate Table
        self.fitted_curve_info_table = self.fitted_curve_info_plot.table(
            cellText=self.get_fitted_curve_info(),
            colLabels=None,
            loc="center",
            cellLoc="center",
        )
        # "Pomote" first row to "tilte"
        self.promote_first_table_row_to_title(self.fitted_curve_info_table)

    def plot_fitted_curve(self):
        self.time_domain_plot.plot(
            self.curve_fitter.time_scatter_values,
            self.curve_fitter.approximated_amplitude_scatter_values,
        )

    def on_click(
        self,
        event: MouseEvent,
        scatter: PathCollection,
        ax: Axes,
        annotations: List[Annotation] | None,
    ) -> None:
        """Handles mouse click events for adding/removing points interactively."""
        if event.key == "control":
            # bypass point addition / removal
            return 


        if event.button == MouseButton.LEFT and event.inaxes:
            self.add_point(event, scatter, ax, annotations)
            self.generate_curve_fit()
        elif event.button == MouseButton.RIGHT and event.inaxes:
            self.remove_point(event, scatter, annotations)
            self.generate_curve_fit()

        event.canvas.draw()

    def on_plot_click(self, event: MouseEvent):
        """Handles mouse click events for adding/removing points interactively."""
        if event.inaxes == self.time_domain_plot:
            self.on_click(
                event,
                self.time_scatter_data,
                self.time_domain_plot,
                None,
            )
        elif event.inaxes == self.frequency_domain_plot:
            self.on_click(
                event,
                self.frequency_scatter_data,
                self.frequency_domain_plot,
                self.frequency_scatter_annotations,
            )

    def add_point(
        self,
        event: MouseEvent,
        scatter: PathCollection,
        ax: Axes,
        annotations: List[Annotation] | None,
    ) -> None:
        """Adds a point to the scatter plot on left-click."""
        existing_points = scatter.get_offsets()

        if len(existing_points) == 0:
            new_points = np.array([[event.xdata, event.ydata]])
        else:
            new_points = np.vstack([existing_points, [event.xdata, event.ydata]])

        scatter.set_offsets(new_points)  # Update scatter plot


        if ax == self.frequency_domain_plot and annotations is not None:
            # Only show frequency data labels
            annotation = ax.annotate(
                f"({event.xdata:.1f}Hz)",
                (event.xdata, event.ydata),
                textcoords="offset points",
                xytext=(5, 5),
                ha="left",
                color="red",
            )
            annotations.append(annotation)

        ax.figure.canvas.draw()  # Redraw plot

    def remove_point(
        self, event: MouseEvent, scatter: PathCollection, annotations: List[Annotation] | None
    ) -> None:
        """Removes the nearest point and updates scatter data properly."""
        if scatter.get_offsets().shape[0] == 0:
            return  # No points to remove

        distances = np.linalg.norm(
            scatter.get_offsets() - np.array([event.xdata, event.ydata]), axis=1
        )
        index = int(np.argmin(distances))

        new_offsets = np.delete(scatter.get_offsets(), index, axis=0)
        scatter.set_offsets(new_offsets)

        if annotations is not None:
            annotations[index].remove()
            annotations.pop(index)

        # Force an update to scatter data in the curve fitter
        self.curve_fitter.time_domain_scatter_data = scatter

        scatter.figure.canvas.draw()  # Redraw plot

    def on_close(self, event: CloseEvent) -> None:
        """Handles the close event, prompting to save amplitude_data."""

        root = tk.Tk()
        root.withdraw()
        save_prompt = messagebox.askyesno("Save Data", "Do you want to save the data?")

        if save_prompt:
            save_all_data(
                file_base_name=self.wav_file.friendly_identifier,
                time_data=self.time_data,
                amplitude_data=self.amplitude_data,
                freq_data=self.freq_data,
                magnitude_data=self.magnitude_data,
                time_scatter_data=self.time_scatter_data,
                frequency_scatter_data=self.frequency_scatter_data,
                figure=self.figure,
                wav_file=self.wav_file
            )

            # Save figure
            # self.figure.savefig(f"{self.wav_file.friendly_identifier}_plot.png")
            print("Data and plot saved.")

    def generate_curve_fit(self):
        if len(self.time_scatter_data.get_offsets()) > 4:
            self.curve_fitter.time_domain_scatter_data = (
                self.time_scatter_data
            )  # Make sure it's assigned
            self.curve_fitter.solve()
            self.update_dynamic_plots()

    def update_dynamic_plots(self):
        # update "dynamic results" as we add more scatter points and re-solve the curve fitting
        self.update_scatter_points()
        self.update_fitted_curve()
        self.update_fitted_curve_table()

    def update_scatter_points(self):
        """Updates the scatter plot dynamically when new points are added."""
        if self.time_scatter_data:
            self.time_scatter_data.set_offsets(
                self.curve_fitter.time_domain_scatter_data.get_offsets()
            )
            self.figure.canvas.draw()

    def update_fitted_curve(self):
        """Updates the fitted curve dynamically instead of re-plotting it."""
        if self.curve_fitter.solved_parameters is None:
            print("Curve fitting failed. Cannot update fitted curve.")
            return  # Exit early

        if self.fitted_curve_line is None:
            # First-time creation
            (self.fitted_curve_line,) = self.time_domain_plot.plot(
                self.curve_fitter.time_scatter_values,
                self.curve_fitter.approximated_amplitude_scatter_values,
                color="red",  # Red line for fitted curve
                label="Fitted Curve",
                linestyle="--"
            )
            self.time_domain_plot.legend()
        else:
            # Update the existing fitted curve line
            self.fitted_curve_line.set_xdata(self.curve_fitter.time_scatter_values)
            self.fitted_curve_line.set_ydata(
                self.curve_fitter.approximated_amplitude_scatter_values
            )

        self.figure.canvas.draw()

    def update_fitted_curve_table(self):
        """Updates the fitted curve parameter table dynamically, ensuring cell keys exist."""
        if self.fitted_curve_info_table:
            new_data = self.get_fitted_curve_info()  # Fetch updated values

            # Ensure row counts match before updating
            for row_idx, row in enumerate(new_data):
                for col_idx, text in enumerate(row):
                    cell_key = (row_idx, col_idx)
                    if cell_key in self.fitted_curve_info_table._cells:
                        self.fitted_curve_info_table[cell_key].get_text().set_text(text)
                    else:
                        print(
                            f"Warning: Table cell {cell_key} not found. Skipping update."
                        )

            self.figure.canvas.draw()
