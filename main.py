import numpy as np
import matplotlib.pyplot as plt
import scipy.io.wavfile as wav
import scipy.fftpack as fft

def on_click(event, scatter, ax, annotations):
    """Handles mouse click events: left-click to add a point, right-click to remove a point."""
    if event.button == 1 and event.inaxes:  # Left-click to add a point
        scatter.set_offsets(np.append(scatter.get_offsets(), [[event.xdata, event.ydata]], axis=0))
        annotation = ax.annotate(f'({event.xdata:.2f}, {event.ydata:.2f})', (event.xdata, event.ydata),
                                 textcoords="offset points", xytext=(5,5), ha='left', color='red')
        annotations.append(annotation)
        event.canvas.draw()
    elif event.button == 3 and event.inaxes:  # Right-click to remove the nearest point
        if len(scatter.get_offsets()) > 0:
            distances = np.linalg.norm(scatter.get_offsets() - np.array([event.xdata, event.ydata]), axis=1)
            index = np.argmin(distances)
            new_offsets = np.delete(scatter.get_offsets(), index, axis=0)
            scatter.set_offsets(new_offsets)
            
            annotations[index].remove()
            annotations.pop(index)
            
            event.canvas.draw()

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
    time = np.linspace(0., N / sample_rate, N)
    
    # Plot time domain and frequency domain in a single figure
    fig, axs = plt.subplots(2, 1, figsize=(10, 8))
    
    # Time domain plot
    axs[0].plot(time, data)
    axs[0].set_title(f"Time Domain Representation - {wav_file}")
    axs[0].set_xlabel("Time (seconds)")
    axs[0].set_ylabel("Amplitude")
    axs[0].grid()
    time_scatter = axs[0].scatter([], [], color='red')  # Interactive points
    time_annotations = []
    
    # Frequency domain plot
    axs[1].plot(freq[:N // 2], np.abs(freq_data[:N // 2]) / N)  # Plot only positive frequencies
    axs[1].set_title(f"Frequency Domain Representation - {wav_file}")
    axs[1].set_xlabel("Frequency (Hz)")
    axs[1].set_ylabel("Magnitude")
    axs[1].grid()
    freq_scatter = axs[1].scatter([], [], color='red')  # Interactive points
    freq_annotations = []
    
    # Connect click events to both subplots
    fig.canvas.mpl_connect('button_press_event', 
                           lambda event: on_click(event, time_scatter, axs[0], time_annotations) if event.inaxes == axs[0] 
                           else on_click(event, freq_scatter, axs[1], freq_annotations))
    
    plt.tight_layout()
    plt.show()

# Example usage:
wav_file_path = "hit2-1.wav"  # Change this to your actual file path
plot_frequency_spectrum(wav_file_path)

