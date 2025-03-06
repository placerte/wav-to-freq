import numpy as np
import matplotlib.pyplot as plt
import scipy.io.wavfile as wav
import scipy.fftpack as fft

def plot_frequency_spectrum(wav_file):
    # Read the WAV file
    sample_rate, data = wav.read(wav_file)
    
    # If stereo, take only one channel
    if len(data.shape) > 1:
        data = data[:, 0]
    
    # Compute the FFT
    N = len(data)  # Number of samples
    T = 1.0 / sample_rate  # Sampling interval
    freq_data = fft.fft(data)
    freq = np.fft.fftfreq(N, T)
    
    # Plot the frequency domain
    plt.figure(figsize=(10, 6))
    plt.plot(freq[:N // 2], np.abs(freq_data[:N // 2]) / N)  # Plot only positive frequencies
    plt.title(f"Frequency Domain Representation - {wav_file}")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.grid()
    plt.show()

# Example usage:
wav_file_path = "hit2-1.wav"  # Change this to your actual file path
plot_frequency_spectrum(wav_file_path)

