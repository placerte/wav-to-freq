from file_handler import save_all_data
from computing import compute_fft, curve_fit

import numpy as np
import matplotlib.pyplot as plt

import matplotlib.gridspec as gridspec
from matplotlib.table import Table
from matplotlib.axes import Axes
from matplotlib.text import Annotation
from matplotlib.collections import Collection, PathCollection
from matplotlib.backend_bases import MouseEvent, CloseEvent
from matplotlib.figure import Figure

from numpy.typing import ArrayLike
from typing import List

import tkinter as tk
from tkinter import messagebox

class Plotter():

    wav_filepath: str
    file_base_name: str

    time_data: np.ndarray
    amplitude_data: np.ndarray
    freq_data: np.ndarray
    magnitude_data: np.ndarray
    time_scatter_data: PathCollection
    time_scatter_annotations: list[Annotation]
    frequency_scatter_data: PathCollection
    frequency_scatter_annotations: list[Annotation]

    figure: Figure

    def __init__(self, wav_filepath: str, file_base_name: str) -> None:
        self.wav_filepath = wav_filepath
        self.file_base_name = file_base_name

    def plot_time_domain(self, ax: Axes) -> tuple[Collection, list[Annotation]]:
        """Plots the time_data-domain representation."""
        ax.plot(self.time_data, self.amplitude_data)
        ax.set_title(f"Time Domain Representation - {self.wav_filepath}")
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Amplitude")
        ax.grid()
        return ax.scatter([], [], color='red'), []  # Interactive points & annotations list

    def plot_frequency_domain(self, ax: Axes, N: int) -> tuple[Collection, list[Annotation]]:
        """Plots the frequency-domain representation."""
        ax.plot(self.freq_data[:N // 2], np.abs(self.magnitude_data[:N // 2]) / N)
        ax.set_title(f"Frequency Domain Representation - {self.wav_filepath}")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Magnitude")
        ax.grid()
        return ax.scatter([], [], color='red'), []  # Interactive points & annotations list

    def add_point(self, event: MouseEvent, scatter: PathCollection, ax: Axes, annotations: List[Annotation]) -> None:
        """Adds a point to the plot on left-click."""
        scatter.set_offsets(np.append(scatter.get_offsets(), [[event.xdata, event.ydata]], axis=0))
        annotation: Annotation = ax.annotate(f'({event.xdata:.4f}, {event.ydata:.4f})',
                                                 (event.xdata, event.ydata),
                                                 textcoords="offset points", xytext=(5,5), ha='left', color='red')
        annotations.append(annotation)
        event.canvas.draw()

    def remove_point(self, event: MouseEvent, scatter: PathCollection, annotations: List[Annotation]) -> None:
        """Removes the nearest point on right-click."""
        if len(scatter.get_offsets()) > 0:
            distances: np.ndarray = np.linalg.norm(scatter.get_offsets() - np.array([event.xdata, event.ydata]), axis=1)
            index: int = int(np.argmin(distances))
            scatter.set_offsets(np.delete(scatter.get_offsets(), index, axis=0))
            annotations[index].remove()
            annotations.pop(index)
        event.canvas.draw()

    def on_click(self, event: MouseEvent, scatter: PathCollection, ax: Axes, annotations: List[Annotation]) -> None:
        """Handles mouse click events for adding/removing points interactively."""
        if event.button == 1 and event.inaxes:
            self.add_point(event, scatter, ax, annotations)
        elif event.button == 3 and event.inaxes:
            self.remove_point(event, scatter, annotations)

    def on_close(self, event: CloseEvent) -> None:
        """Handles the close event, prompting to save amplitude_data."""
        
        root = tk.Tk()
        root.withdraw()
        save_prompt = messagebox.askyesno("Save Data", "Do you want to save the data?")
        
        if save_prompt:
            save_all_data(file_base_name =self.file_base_name,
                          time_data = self.time_data,
                          amplitude_data = self.amplitude_data,
                          freq_data = self.freq_data,
                          magnitude_data = self.magnitude_data,
                          time_scatter_data = self.time_scatter_data,
                          frequency_scatter_data = self.frequency_scatter_data)

            # Save figure
            self.figure.savefig(f"{self.file_base_name}_plot.png")
            print("Data and plot saved.")

    def get_table_data(self) -> list[list[str]]:
        """Generates metadata for the plots"""
        return [
            ["File", self.file_base_name],
            ["Other", "blabla"],
            ["Other", "blabla"],
            ["Other", "blabla"],
            ["Other", "blabla"],
            ["Other", "blabla"],
            ["Other", "blabla"],
            ["Other", "blabla"]
        ]

    def generate_curve_fit(self):
        if len(self.time_scatter_data.get_offsets()) > 4:
            curve_fit #  RENDU ICI
        
    def generate_plots(self) -> None:
        """Plots both time_data and frequency domain representations with interactive points."""
        self.time_data, self.amplitude_data, self.freq_data, self.magnitude_data, N = compute_fft(self.wav_filepath)

        self.figure = plt.figure(figsize=(12,6))
        spec: gridspec.GridSpec = gridspec.GridSpec(nrows=2, ncols=2, width_ratios=[4,1])

        #fig, axs = plt.subplots(2, 1, figsize=(10, 8))
        
        # Time-domain plot
        ax_time: Axes = self.figure.add_subplot(spec[0,0])
        self.time_scatter_data, self.time_scatter_annotations = self.plot_time_domain(ax_time)
        
        # Frequency-domain plot
        ax_freq: Axes = self.figure.add_subplot(spec[1,0])
        self.frequency_scatter_data, self.frequency_scatter_annotations = self.plot_frequency_domain(ax_freq, N)
        
        # Generate table info
        ax_table: Axes = self.figure.add_subplot(spec[:, 1])
        ax_table.axis("off")
        table_data: list[list[str]] = self.get_table_data()
        table: Table = ax_table.table(cellText=table_data, colLabels=["Property", "Value"], loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        #table.scale(1.2, 2.0)

        # Interactive click event handling
        self.figure.canvas.mpl_connect('button_press_event', 
                               lambda event: self.on_click(event, self.time_scatter_data, ax_time, self.time_scatter_annotations)
                               if event.inaxes == ax_time 
                               else self.on_click(event, self.frequency_scatter_data, ax_freq, self.frequency_scatter_annotations))
        
        

        plt.tight_layout()
        self.figure.canvas.mpl_connect('close_event', lambda event: self.on_close(event))
        plt.show()


