import csv
from ntpath import basename
import os

import numpy as np
import matplotlib.pyplot as plt

from matplotlib.axes import Axes
from matplotlib.text import Annotation
from matplotlib.collections import Collection, PathCollection
from matplotlib.backend_bases import MouseEvent, CloseEvent
from matplotlib.figure import Figure

from numpy.typing import ArrayLike
import scipy.io.wavfile as wav
import scipy.fftpack as fft
from typing import Tuple, List

import tkinter as tk
from tkinter import messagebox, filedialog

def compute_fft(wav_filepath: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    """Reads a WAV file and computes its FFT."""
    sample_rate, data = wav.read(wav_filepath)
    if len(data.shape) > 1:
        data = data[:, 0]  # Convert stereo to mono
    
    N: int = len(data)
    T: float = 1.0 / sample_rate
    freq_data: np.ndarray = fft.fft(data)
    freq: np.ndarray = np.fft.fftfreq(N, T)
    time: np.ndarray = np.linspace(0., N / sample_rate, N)
    
    return time, data, freq, freq_data, N

def plot_time_domain(ax: Axes, time: np.ndarray, data: np.ndarray, wav_filepath: str) -> Tuple[Collection, List[Annotation]]:
    """Plots the time-domain representation."""
    ax.plot(time, data)
    ax.set_title(f"Time Domain Representation - {wav_filepath}")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Amplitude")
    ax.grid()
    return ax.scatter([], [], color='red'), []  # Interactive points & annotations list

def plot_frequency_domain(ax: Axes, freq: np.ndarray, freq_data: np.ndarray, N: int, wav_filepath: str) -> Tuple[Collection, List[Annotation]]:
    """Plots the frequency-domain representation."""
    ax.plot(freq[:N // 2], np.abs(freq_data[:N // 2]) / N)
    ax.set_title(f"Frequency Domain Representation - {wav_filepath}")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude")
    ax.grid()
    return ax.scatter([], [], color='red'), []  # Interactive points & annotations list

def add_point(event: MouseEvent, scatter: PathCollection, ax: Axes, annotations: List[Annotation]) -> None:
    """Adds a point to the plot on left-click."""
    scatter.set_offsets(np.append(scatter.get_offsets(), [[event.xdata, event.ydata]], axis=0))
    annotation: Annotation = ax.annotate(f'({event.xdata:.4f}, {event.ydata:.4f})',
                                             (event.xdata, event.ydata),
                                             textcoords="offset points", xytext=(5,5), ha='left', color='red')
    annotations.append(annotation)
    event.canvas.draw()

def remove_point(event: MouseEvent, scatter: PathCollection, annotations: List[Annotation]) -> None:
    """Removes the nearest point on right-click."""
    if len(scatter.get_offsets()) > 0:
        distances: np.ndarray = np.linalg.norm(scatter.get_offsets() - np.array([event.xdata, event.ydata]), axis=1)
        index: int = np.argmin(distances)
        scatter.set_offsets(np.delete(scatter.get_offsets(), index, axis=0))
        annotations[index].remove()
        annotations.pop(index)
    event.canvas.draw()

def on_click(event: MouseEvent, scatter: PathCollection, ax: Axes, annotations: List[Annotation]) -> None:
    """Handles mouse click events for adding/removing points interactively."""
    if event.button == 1 and event.inaxes:
        add_point(event, scatter, ax, annotations)
    elif event.button == 3 and event.inaxes:
        remove_point(event, scatter, annotations)

def save_time_domain_data(basename: str, time: np.ndarray, data: np.ndarray):

    filename: str = f"{basename}_time_domain.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time (s)", "Amplitude"])
        writer.writerows(zip(time, data))

def save_frequency_domain_data(basename: str, freq: np.ndarray, freq_data: np.ndarray, data: np.ndarray):

    filename: str = f"{basename}_frequency_domain.csv"

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Frequency (Hz)", "Magnitude"])
        writer.writerows(zip(freq[:len(freq)//2], np.abs(freq_data[:len(freq)//2]) / len(data)))

def save_time_scatter_points(base_name: str, time_scatter_data: PathCollection):
    
    filename: str = f"{base_name}_time_scatter_points.csv"

    points = time_scatter_data.get_offsets().tolist()

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time (s)","Amplitude"])
        writer.writerows(points)

def save_frequency_scatter_points(base_name: str, frequency_scatter_data: PathCollection):

    filename: str = f"{base_name}_frequency_scatter_points.csv"

    points = frequency_scatter_data.get_offsets().tolist()

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Frequency (Hz)","Magnitude"])
        writer.writerows(points)


def on_close(event: CloseEvent, fig: Figure, time: np.ndarray,
             data: np.ndarray, freq: np.ndarray, freq_data: np.ndarray,
             time_scatter_data: PathCollection, frequency_scatter_data: PathCollection, 
             wav_filepath: str) -> None:
    """Handles the close event, prompting to save data."""
    
    root = tk.Tk()
    root.withdraw()
    save_prompt = messagebox.askyesno("Save Data", "Do you want to save the data?")
    
    if save_prompt:
        base_name = os.path.splitext(wav_filepath)[0]
        
        save_time_domain_data(base_name, time, data)
        save_time_scatter_points(base_name, time_scatter_data)

        save_frequency_domain_data(base_name, freq, freq_data, data) 
        save_frequency_scatter_points(base_name, frequency_scatter_data)

        # Save figure
        fig.savefig(f"{base_name}_plot.png")
        print("Data and plot saved.")

def plot_frequency_spectrum(wav_filepath: str) -> None:
    """Plots both time and frequency domain representations with interactive points."""
    time, data, freq, freq_data, N = compute_fft(wav_filepath)
    fig, axs = plt.subplots(2, 1, figsize=(10, 8))
    
    # Time-domain plot
    time_scatter, time_annotations = plot_time_domain(axs[0], time, data, wav_filepath)
    
    # Frequency-domain plot
    freq_scatter, freq_annotations = plot_frequency_domain(axs[1], freq, freq_data, N, wav_filepath)
    
    # Interactive click event handling
    fig.canvas.mpl_connect('button_press_event', 
                           lambda event: on_click(event, time_scatter, axs[0], time_annotations)
                           if event.inaxes == axs[0] 
                           else on_click(event, freq_scatter, axs[1], freq_annotations))
    
    plt.tight_layout()
    fig.canvas.mpl_connect('close_event', lambda event: on_close(event, fig, time, data, freq, freq_data, time_scatter, freq_scatter, wav_filepath))
    plt.show()

# Example usage:
wav_filepath = "hit2-1.wav"  # Change to your actual file path
plot_frequency_spectrum(wav_filepath)

