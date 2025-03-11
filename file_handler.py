import csv
import os
from matplotlib.collections import PathCollection
import numpy as np

def get_first_wav_filepath(in_directory:str = "./")->tuple[str, str]:
    file: str
    
    for file in os.listdir(in_directory):
        if file.lower().endswith(".wav"):
            
            wav_filepath = os.path.join(in_directory, file)
            file_base_name = os.path.splitext(wav_filepath)[0]
            
            return file_base_name, wav_filepath
    
    return "", ""


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

