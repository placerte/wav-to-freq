import csv
from datetime import date, datetime
from nt import stat_result
import os
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
import numpy as np
import wave
import shutil
import tkinter
from tkinter import messagebox

class WavSampleFile:
    filepath: str
    sample_rate: int
    duration: float
    channel_count: int
    creation_datetime: datetime
    modification_datetime: datetime

    @property
    def filename_without_extension(self) -> str:
        return os.path.splitext(os.path.basename(self.filepath))[0]

    @property
    def filename_with_extension(self) -> str:
        return os.path.basename(self.filepath)

    @property
    def creation_date(self) -> date:
        return self.creation_datetime.date()

    @property
    def modification_date(self) -> date:
        return self.modification_datetime.date()

    @property
    def friendly_identifier(self) -> str:
        return f"{self.creation_date} - {self.filename_without_extension}"

    def get_first_wav_filepath(self, in_directory: str = "./"):

        file: str

        for file in os.listdir(in_directory):
            if file.lower().endswith(".wav"):
                self.filepath = os.path.join(in_directory, file)
                self.get_wav_file_metadata()

    def get_wav_file_metadata(self):
        wav_file: wave.Wave_read = wave.open(self.filepath, "rb")
        other_file_stats: stat_result = os.stat(self.filepath)

        self.sample_rate = wav_file.getframerate()
        self.duration = float(wav_file.getnframes() / wav_file.getframerate())
        self.channel_count = wav_file.getnchannels()

        self.creation_datetime = datetime.fromtimestamp(other_file_stats.st_birthtime)
        self.modification_datetime = datetime.fromtimestamp(other_file_stats.st_mtime)

    def __str__(self) -> str:
        return f"Filepath: {self.filepath}, sample_rate= {self.sample_rate}Hz, duration= {self.duration}, channel count= {self.channel_count}, creation datetime: {self.creation_datetime}, modification date: {self.modification_datetime}"

    def __init__(self, filepath=""):
        self.filepath = filepath
        self.sample_rate = 0
        self.duration = 0.0
        self.channel_count = 0
        self.creation_datetime = datetime(1900, 1, 1)
        self.modification_datetime = datetime(1900, 1, 1)

        if self.filepath != "":
            self.get_wav_file_metadata()


def save_time_domain_data(
    file_base_path: str, time_data: np.ndarray, amplitude_data: np.ndarray):

    file_path: str = f"{file_base_path}_time_domain.csv"

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Time (s)", "Amplitude"])
        writer.writerows(zip(time_data, amplitude_data))


def save_frequency_domain_data(
    file_base_path: str,
    freq_data: np.ndarray,
    magnitude_data: np.ndarray,
    amplitude_data: np.ndarray
):

    file_path: str = f"{file_base_path}_frequency_domain.csv"

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Frequency (Hz)", "Magnitude"])
        writer.writerows(
            zip(
                freq_data[: len(freq_data) // 2],
                np.abs(magnitude_data[: len(freq_data) // 2]) / len(amplitude_data),
            )
        )


def save_time_scatter_points(file_base_path: str, time_scatter_data: PathCollection):

    file_path: str = f"{file_base_path}_time_scatter_points.csv"

    points = time_scatter_data.get_offsets().tolist()

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Time (s)", "Amplitude"])
        writer.writerows(points)

def save_frequency_scatter_points(
        file_base_path: str, frequency_scatter_data: PathCollection):

    file_path: str = f"{file_base_path}_frequency_scatter_points.csv"

    points = frequency_scatter_data.get_offsets().tolist()

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Frequency (Hz)", "Magnitude"])
        writer.writerows(points)


def create_directory(directory_path: str, force_overwrite: bool=False, show_overwrite_prompt: bool=True)->bool:

    # Logical tests
    directory_exists: bool = os.path.exists(directory_path)
    accept_overwrite: bool = False

    if directory_exists and show_overwrite_prompt:
        accept_overwrite = messagebox.askyesno("Overwrite existing directory?", f"The directory {directory_path} already exists. Do you want to overwrite it and clear all its current content?")
    
    # Appropriate actions
    if directory_exists == False:
        os.mkdir(directory_path)
        return True
    elif force_overwrite or accept_overwrite:
        shutil.rmtree(directory_path)
        os.mkdir(directory_path)
        return True
    else:
        return False
def move_wav_file(wav_file: WavSampleFile, destination_directory: str):
    shutil.move(src=wav_file.filepath, dst=destination_directory+wav_file.filename_with_extension) 


def save_all_data(
    file_base_name: str,
    time_data: np.ndarray,
    amplitude_data: np.ndarray,
    freq_data: np.ndarray,
    magnitude_data: np.ndarray,
    time_scatter_data: PathCollection | None,
    frequency_scatter_data: PathCollection | None,
    figure: Figure,
    wav_file: WavSampleFile,
    put_in_sub_directory: bool = True
):

    file_base_dir: str

    if put_in_sub_directory:
        file_base_dir = "./" + file_base_name + "/"
        os.mkdir(file_base_dir)
        move_wav_file(wav_file, file_base_dir)
    else:
        file_base_dir = "./" + file_base_name

    file_base_path = file_base_dir + file_base_name

    save_time_domain_data(file_base_path, time_data, amplitude_data)
    save_frequency_domain_data(
        file_base_path, freq_data, magnitude_data, amplitude_data)
    if time_scatter_data is not None:
        save_time_scatter_points(file_base_path, time_scatter_data)
    if frequency_scatter_data is not None:
        save_frequency_scatter_points(file_base_path, frequency_scatter_data)

    figure.savefig(file_base_path + "_plot.png")
