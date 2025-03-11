import os

from file_handler import save_all_data
from computing import compute_fft

import numpy as np
import matplotlib.pyplot as plt

from matplotlib.axes import Axes
from matplotlib.text import Annotation
from matplotlib.collections import Collection, PathCollection
from matplotlib.backend_bases import MouseEvent, CloseEvent
from matplotlib.figure import Figure

from numpy.typing import ArrayLike
from typing import Tuple, List

import tkinter as tk
from tkinter import messagebox

class Plotter():

    wav_filepath: str
    file_base_name: str

    def __init__(self, wav_filepath: str, file_base_name: str) -> None:
        self.wav_filepath = wav_filepath
        self.file_base_name = file_base_name

    def plot_time_domain(self, ax: Axes, time_data: np.ndarray, amplitude_data: np.ndarray, wav_filepath: str) -> Tuple[Collection, List[Annotation]]:
        """Plots the time_data-domain representation."""
        ax.plot(time_data, amplitude_data)
        ax.set_title(f"Time Domain Representation - {wav_filepath}")
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Amplitude")
        ax.grid()
        return ax.scatter([], [], color='red'), []  # Interactive points & annotations list

    def plot_frequency_domain(self, ax: Axes, freq_data: np.ndarray, magnitude_data: np.ndarray, N: int, wav_filepath: str) -> Tuple[Collection, List[Annotation]]:
        """Plots the frequency-domain representation."""
        ax.plot(freq_data[:N // 2], np.abs(magnitude_data[:N // 2]) / N)
        ax.set_title(f"Frequency Domain Representation - {wav_filepath}")
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



    def on_close(self, event: CloseEvent, fig: Figure, time_data: np.ndarray,
                 amplitude_data: np.ndarray, freq_data: np.ndarray, magnitude_data: np.ndarray,
                 time_scatter_data: PathCollection, frequency_scatter_data: PathCollection, 
                 wav_filepath: str) -> None:
        """Handles the close event, prompting to save amplitude_data."""
        
        root = tk.Tk()
        root.withdraw()
        save_prompt = messagebox.askyesno("Save Data", "Do you want to save the data?")
        
        if save_prompt:
            save_all_data(file_base_name=self.file_base_name,
                          time_data= time_data,
                          amplitude_data=amplitude_data,
                          freq_data=freq_data,
                          magnitude_data=magnitude_data,
                          time_scatter_data=time_scatter_data,
                          frequency_scatter_data= frequency_scatter_data)

            # Save figure
            fig.savefig(f"{self.file_base_name}_plot.png")
            print("Data and plot saved.")

    def generate_plots(self) -> None:
        """Plots both time_data and frequency domain representations with interactive points."""
        time_data, amplitude_data, freq_data, magnitude_data, N = compute_fft(self.wav_filepath)
        fig, axs = plt.subplots(2, 1, figsize=(10, 8))
        
        # Time-domain plot
        time_scatter, time_annotations = self.plot_time_domain(axs[0], time_data, amplitude_data, self.wav_filepath)
        
        # Frequency-domain plot
        freq_scatter, freq_annotations = self.plot_frequency_domain(axs[1], freq_data, magnitude_data, N, self.wav_filepath)
        
        # Interactive click event handling
        fig.canvas.mpl_connect('button_press_event', 
                               lambda event: self.on_click(event, time_scatter, axs[0], time_annotations)
                               if event.inaxes == axs[0] 
                               else self.on_click(event, freq_scatter, axs[1], freq_annotations))
        
        plt.tight_layout()
        fig.canvas.mpl_connect('close_event', lambda event: self.on_close(event, fig, time_data, amplitude_data, freq_data, magnitude_data, time_scatter, freq_scatter, self.wav_filepath))
        plt.show()


