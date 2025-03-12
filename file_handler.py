import csv
from datetime import date, datetime
from nt import stat_result
import os
from matplotlib.collections import PathCollection
import numpy as np
import wave


class WavSampleFile():
    filepath: str
    sample_rate: int
    duration: float
    channel_count: int
    creation_datetime: datetime
    modification_datetime: datetime
    
    @property
    def filename_without_extension(self)->str:
        return os.path.splitext(os.path.basename(self.filepath))[0]

    @property
    def filename_with_extension(self)->str:
        return os.path.basename(self.filepath)

    @property
    def creation_date(self)-> date:
        return self.creation_datetime.date()

    @property
    def modification_date(self)->date:
        return self.modification_datetime.date()

    @property
    def friendly_identifier(self)->str:
        return f"{self.creation_date} - {self.filename_without_extension}"

    def get_first_wav_filepath(self, in_directory:str = "./"):
        
        file: str
        
        for file in os.listdir(in_directory):
            if file.lower().endswith(".wav"):
                self.filepath = os.path.join(in_directory, file)
                self.get_wav_file_metadata()
        
    def get_wav_file_metadata(self):
        wav_file: wave.Wave_read =  wave.open(self.filepath, "rb")
        other_file_stats: stat_result = os.stat(self.filepath)

        self.sample_rate =  wav_file.getframerate()
        self.duration = float(wav_file.getnframes()/wav_file.getframerate())
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
        self.creation_datetime = datetime(1900,1,1)
        self.modification_datetime = datetime(1900,1,1)

        if self.filepath != "":
            self.get_wav_file_metadata()

        


def save_time_domain_data(file_base_name: str, time_data: np.ndarray, amplitude_data: np.ndarray):

    filename: str = f"{file_base_name}_time_domain.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time (s)", "Amplitude"])
        writer.writerows(zip(time_data, amplitude_data))

def save_frequency_domain_data(file_base_name: str, freq_data: np.ndarray, magnitude_data: np.ndarray, amplitude_data: np.ndarray):

    filename: str = f"{file_base_name}_frequency_domain.csv"

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Frequency (Hz)", "Magnitude"])
        writer.writerows(zip(freq_data[:len(freq_data)//2], np.abs(magnitude_data[:len(freq_data)//2]) / len(amplitude_data)))

def save_time_scatter_points(file_base_name: str, time_scatter_data: PathCollection):
    
    filename: str = f"{file_base_name}_time_scatter_points.csv"

    points = time_scatter_data.get_offsets().tolist()

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time (s)","Amplitude"])
        writer.writerows(points)

def save_frequency_scatter_points(file_base_name: str, frequency_scatter_data: PathCollection):

    filename: str = f"{file_base_name}_frequency_scatter_points.csv"

    points = frequency_scatter_data.get_offsets().tolist()

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Frequency (Hz)","Magnitude"])
        writer.writerows(points)

def save_all_data(file_base_name: str,
                  time_data: np.ndarray, 
                  amplitude_data: np.ndarray,
                  freq_data: np.ndarray,
                  magnitude_data: np.ndarray,
                  time_scatter_data: PathCollection,
                  frequency_scatter_data: PathCollection):
    save_time_domain_data(file_base_name, time_data, amplitude_data)
    save_frequency_domain_data(file_base_name, freq_data, magnitude_data, amplitude_data)
    save_time_scatter_points(file_base_name, time_scatter_data)
    save_frequency_scatter_points(file_base_name, frequency_scatter_data)

