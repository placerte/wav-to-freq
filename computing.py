import numpy as np
from pandas.core.api import DataFrame
from scipy.optimize import curve_fit
import pandas as pd
import scipy.io.wavfile as wav
import scipy.fftpack as fft

def compute_fft(wav_filepath: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    """Reads a WAV file and computes its FFT."""
    sample_rate, amplitude_data = wav.read(wav_filepath)
    if len(amplitude_data.shape) > 1:
        amplitude_data = amplitude_data[:, 0]  # Convert stereo to mono
    
    N: int = len(amplitude_data)
    T: float = 1.0 / sample_rate
    magnitude_data: np.ndarray = fft.fft(amplitude_data)
    freq_data: np.ndarray = np.fft.fftfreq(N, T)
    time_data: np.ndarray = np.linspace(0., N / sample_rate, N)
    
    return time_data, amplitude_data, freq_data, magnitude_data, N

#Curve to fit
def custom_curve(t_i: float, t_offset: float, a_offset: float, zeta_2pi_fn: float, a_0: float)->float:
    a_i: float =  a_0 * np.exp(-zeta_2pi_fn*(t_i-t_offset))+a_offset

    return a_i

def read_data_file(csv_filepath:str)->tuple[pd.Series, pd.Series]:
    df: DataFrame = pd.read_csv(csv_filepath)
    x: pd.Series = df.iloc[:, 0].values # all rows, only column 0
    y: pd.Series = df.iloc[:, 1].values # all rows, only column 1

    return (x, y)

def guess_initial_t_offset(t_i_data: pd.Series)-> float:
    # t_offset guess is based on the minimal t value from the data set.
    # it could be more or less, but this will give us an valid order
    return np.min(t_i_data)

def guess_initial_A_offset(a_i_data: pd.Series)-> float:
    # We want our curve to meet 0 at t -> inf. so our first guess for A_offset is
    # the minimal value of a_i_data. Since a_i_data are the peaks of the time series
    # it is expected that is is over 0.
    return np.min(a_i_data)

def guess_initial_amplitude(a_i_data: pd.Series)->float:
    # A_0 is supposed to be the amplitude a t=0. The only thing we know is that it is probably
    # greater than the shifted max we have in a_i_data.
    return np.max(a_i_data) - np.min(a_i_data)

def guess_initial_natural_frequency(t_i_data: pd.Series)->float:
    # Our best guess at thhis point is the measured damped frequency
    return get_damped_natural_frequency_fd(t_i_data)


def guess_initial_zeta_2pi_fn(t_i_data, zeta_guess: float = 0.3)->float:
    # This one we have to build gradually the compounded value.
    f_mean_frequency: float = guess_initial_natural_frequency(t_i_data)
    # zeta_guess is harcoded here but generally it is expected to be between
    # 1% and 5% for metalic structures
    
    return zeta_guess*2*np.pi*f_mean_frequency
    
def guess_initial_parameters(t_i_data: pd.Series, a_i_data: pd.Series)->list[float]:
    t_offset_guess = guess_initial_t_offset(t_i_data)
    a_offset_guess = guess_initial_A_offset(a_i_data)
    a_0_guess = guess_initial_amplitude(a_i_data)
    zeta_2pi_fn_guess = guess_initial_zeta_2pi_fn(t_i_data)

    return [t_offset_guess,a_offset_guess, zeta_2pi_fn_guess, a_0_guess]

def get_lower_bounds(a_i_data: pd.Series)->np.ndarray:
    # since we are working with milliseconds it is fair to assume +- 1 sec
    t_offset_min: float = -1
    # the Amplitude offset really depend of some stages of signal processing
    # like normalization, gain at input, gain at post process, etc, therefore 
    # assume the worst
    a_offset_min: float = -np.inf
    # A frequency cannot be negative so
    zeta_2pi_fn_min: float = 0
    # We know that A_0 should be greater than the maximum shifted A_i value
    # since we already guess this value, reuse it and put a little buffer for security
    a_0_min: float = guess_initial_amplitude(a_i_data) * 0.99

    return np.array([t_offset_min, a_offset_min, zeta_2pi_fn_min, a_0_min], dtype=float)

def get_upper_bounds()->np.ndarray:
    # since we are working with milliseconds it is fair to assume +- 1 sec
    t_offset_max: float = 1
    # all the other variables have no theorical targetable maxima.
    # they are certainly smaller than infinity, but we don't have a value for it so:
    a_offset_max: float = np.inf
    zeta_2pi_fn_max: float = np.inf
    a_0_max = np.inf

    return np.array([t_offset_max, a_offset_max, zeta_2pi_fn_max, a_0_max], dtype=float)

def get_parameter_bounds(a_i_data: pd.Series)->tuple[np.ndarray,np.ndarray]:
    return (get_lower_bounds(a_i_data), get_upper_bounds())

def get_coefficient_of_determination(t_i_data: pd.Series, a_i_data: pd.Series, solved_parameters: list[float])->float:
    # Retreive the solved parameters
    a_0: float
    zeta_2pi_fn: float
    t_offset: float
    a_offset: float

    t_offset, a_offset, zeta_2pi_fn, a_0 = solved_parameters
    # get predicted values of A(i) using solved parameters
    a_predicted: float = custom_curve(t_i_data, t_offset, a_offset, zeta_2pi_fn, a_0)
    # get the mean value of the actual data
    a_i_mean: float = float(np.mean(a_i_data))

    ss_res: float = np.sum((a_i_data -  a_predicted)**2)
    ss_tot: float = np.sum((a_i_data - a_i_mean)**2)

    r_squared: float = 1 - (ss_res/ss_tot) 

    return r_squared

def print_solved_parameters(solved_parameters: list[float]):
    # Retreive the solved parameters
    a_0: float
    zeta_2pi_fn: float
    t_offset: float
    a_offset: float

    t_offset, a_offset, zeta_2pi_fn, a_0 = solved_parameters
    print(f"Fitted parameters: zeta_2pi_fn={zeta_2pi_fn}, a_0={a_0}, a_offset={a_offset}, t_offset={t_offset}.")

def get_damped_natural_frequency_fd(t_i_data: pd.Series)->float:

    # we can measure the damped frequency by evaluating the mean intervals in t_i_data
    t_invervals: np.ndarray = np.diff(t_i_data)
    tau_mean_period: float = float(np.mean(t_invervals))
    mean_damped_frequency: float = 1/tau_mean_period

    return mean_damped_frequency

def get_natural_frequency_fn(damped_natural_frequency_fd: float,solved_parameters: list[float])->float:
    
    _, _, solved_zeta_2pi_fn, _ = solved_parameters

    term1: float = (2*np.pi*damped_natural_frequency_fd)**2
    term2: float = solved_zeta_2pi_fn**2
    return np.sqrt(term1+term2)/(2*np.pi)

def get_damping_ratio_zeta(damped_natural_frequency_fd: float, natural_frequency_fn: float)->float:
    
    term1: float = (damped_natural_frequency_fd/natural_frequency_fn)**2
    return np.sqrt(1-term1)

