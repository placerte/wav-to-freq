from matplotlib.collections import PathCollection
import numpy as np
from numpy.typing import ArrayLike
from pandas.core.api import DataFrame
from scipy.optimize import curve_fit
import pandas as pd
import scipy.io.wavfile as wav
import scipy.fftpack as fft



#Curve to fit
def damping_envelope_function(t_i: float, t_offset: float, a_offset: float, zeta_omega_n: float, a_0: float)->float:
    a_i: float =  a_0 * np.exp(-zeta_omega_n*(t_i-t_offset))+a_offset
    return a_i


def compute_fft_from_wav_file(wav_filepath: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    """Reads a WAV file and computes its FFT."""
    sample_rate, amplitude_data = wav.read(wav_filepath)
    if len(amplitude_data.shape) > 1:
        amplitude_data = amplitude_data[:, 0]  # Convert stereo to mono
    
    N: int = len(amplitude_data)
    T: float = 1.0 / sample_rate
    magnitude_data: np.ndarray = fft.fft(amplitude_data)
    freq_data: np.ndarray = np.fft.fftfreq(N, T)
    time_data: np.ndarray = np.linspace(0., N / sample_rate, N)
    
    return (time_data, amplitude_data, freq_data, magnitude_data, N)

class DampingEnvelopeCurveParameters():
    a_0: float
    zeta_omega_n: float
    t_offset: float
    a_offset: float

    def __init__(self, a_0: float, zeta_omega_n: float, t_offset: float, a_offset: float) -> None:
        self.a_0 = a_0
        self.zeta_omega_n = zeta_omega_n
        self.t_offset = t_offset
        self.a_offset = a_offset


    def to_ndarray(self)->np.ndarray:
        return np.array([self.t_offset, self.a_offset, self.zeta_omega_n, self.a_0], dtype=float)

    def to_tuple(self)->tuple[float, float, float, float]:
        #return (self.t_offset, self.a_offset, self.zeta_omega_n, self.a_0)
        return tuple(self.to_ndarray())

    def to_list(self)->list[float]:
        return self.to_ndarray().astype(float).tolist()
    
    def __str__(self)->str:

        return f"Curve parameters: zeta_omega_n={self.zeta_omega_n}, a_0={self.a_0}, a_offset={self.a_offset}, t_offset={self.t_offset}."

class DampingEnvelopeCurveFitter():

    time_domain_scatter_data: PathCollection
    initial_parameters_guesses: DampingEnvelopeCurveParameters
    solved_parameters: DampingEnvelopeCurveParameters
    lower_bounds: DampingEnvelopeCurveParameters
    upper_bounds: DampingEnvelopeCurveParameters

    
    @property
    def time_scatter_values(self)-> np.ndarray:

        offsets_arr_like: ArrayLike = self.time_domain_scatter_data.get_offsets()
        offsets: np.ndarray = np.asarray(offsets_arr_like)
        return offsets[:,0]
    
    @property
    def amplitude_scatter_values(self)-> np.ndarray:

        offsets_arr_like: ArrayLike = self.time_domain_scatter_data.get_offsets()
        offsets: np.ndarray = np.asarray(offsets_arr_like)
        return offsets[:,1]

    @property
    def approximated_amplitude_scatter_values(self)-> np.ndarray:
        approx_amps = damping_envelope_function(self.time_scatter_values, *self.solved_parameters.to_list())
        return np.array(approx_amps)

    def guess_initial_t_offset(self)-> float:
        # t_offset guess is based on the minimal t value from the data set.
        # it could be more or less, but this will give us an valid order
        return np.min(self.time_scatter_values)

    def guess_initial_A_offset(self)-> float:
        # We want our curve to meet 0 at t -> inf. so our first guess for A_offset is
        # the minimal value of a_i_data. Since a_i_data are the peaks of the time series
        # it is expected that is is over 0.
        return np.min(self.amplitude_scatter_values)

    def guess_initial_amplitude(self)->float:
        # A_0 is supposed to be the amplitude a t=0. The only thing we know is that it is probably
        # greater than the shifted max we have in a_i_data.
        return np.max(self.amplitude_scatter_values) - np.min(self.amplitude_scatter_values)

    def guess_initial_natural_frequency_omega_n(self)->float:
        # Our best guess at thhis point is the measured damped frequency
        return self.get_damped_natural_frequency_omega_d()


    def guess_initial_zeta_omega_n(self ,zeta_guess: float = 0.03)->float:

        # This one we have to build gradually the compounded value.
        omega_n_guess: float = self.guess_initial_natural_frequency_omega_n()
        # zeta_guess is harcoded here but generally it is expected to be between
        # 1% and 5% for metalic structures
        
        return zeta_guess*omega_n_guess
        
    def guess_initial_parameters(self):
        #the order of parameters must fit damping_envelope_curve()
        t_offset_guess = self.guess_initial_t_offset()
        a_offset_guess = self.guess_initial_A_offset()
        a_0_guess = self.guess_initial_amplitude()
        zeta_omega_n_guess = self.guess_initial_zeta_omega_n()

        self.initial_parameters_guesses = DampingEnvelopeCurveParameters(
                a_0=a_0_guess,
                zeta_omega_n=zeta_omega_n_guess,
                t_offset=t_offset_guess,
                a_offset=a_offset_guess
                )

    def compute_lower_bounds(self):
        # since we are working with milliseconds it is fair to assume +- 1 sec
        t_offset_min: float = -1
        # the Amplitude offset really depend of some stages of signal processing
        # like normalization, gain at input, gain at post process, etc, therefore 
        # assume the worst
        a_offset_min: float = -np.inf
        # A frequency cannot be negative so
        zeta_omega_n_min: float = 0
        # We know that A_0 should be greater than the maximum shifted A_i value
        # since we already guess this value, reuse it and put a little buffer for security
        a_0_min: float = self.guess_initial_amplitude() * 0.99

        self.lower_bounds = DampingEnvelopeCurveParameters(
                a_0=a_0_min,
                zeta_omega_n=zeta_omega_n_min,
                t_offset=t_offset_min,
                a_offset=a_offset_min
                )

    def compute_upper_bounds(self):
        # since we are working with milliseconds it is fair to assume +- 1 sec
        t_offset_max: float = 1
        # all the other variables have no theorical targetable maxima.
        # they are certainly smaller than infinity, but we don't have a value for it so:
        a_offset_max: float = np.inf
        zeta_omega_n_max: float = np.inf
        a_0_max = np.inf

        self.upper_bounds = DampingEnvelopeCurveParameters(
                a_0=a_0_max,
                zeta_omega_n=zeta_omega_n_max,
                t_offset=t_offset_max,
                a_offset=a_offset_max
                )

    def get_parameter_bounds(self)->tuple[np.ndarray,np.ndarray]:
        self.compute_lower_bounds()
        self.compute_upper_bounds()
        return (self.lower_bounds.to_ndarray(), self.upper_bounds.to_ndarray())

    def get_coefficient_of_determination(self)->float:
        # TODO: make sure solved parameters exists
        # get predicted values of A(i) using solved parameters
        a_predicted: float = damping_envelope_function(self.time_scatter_values, *self.solved_parameters.to_list())
        # get the mean value of the actual data
        a_i_mean: float = float(np.mean(self.amplitude_scatter_values))

        ss_res: float = np.sum((self.amplitude_scatter_values -  a_predicted)**2)
        ss_tot: float = np.sum((self.amplitude_scatter_values - a_i_mean)**2)

        r_squared: float = 1 - (ss_res/ss_tot) 

        return r_squared


    def get_damped_natural_frequency_omega_d(self)->float:

        # we can measure the damped frequency by evaluating the mean intervals in t_i_data
        t_invervals: np.ndarray = np.diff(self.time_scatter_values)
        tau_mean_period: float = float(np.mean(t_invervals))
        mean_damped_frequency: float = 2*np.pi/tau_mean_period

        return mean_damped_frequency

    def get_natural_frequency_omega_n(self)->float:
        
        omega_d: float = self.get_damped_natural_frequency_omega_d()
        zeta_omega_n: float = self.solved_parameters.zeta_omega_n

        #TODO: test for solved parameters first
        term1: float = (omega_d)**2
        term2: float = zeta_omega_n**2
        return np.sqrt(term1+term2)

    def get_damping_ratio_zeta(self)->float:
        
        omega_d: float = self.get_damped_natural_frequency_omega_d()
        omega_n: float = self.get_natural_frequency_omega_n()

        term1: float = (omega_d/omega_n)**2
        return np.sqrt(1-term1)

    def solve(self):

        self.guess_initial_parameters()
        list_of_solved_parameters , _= curve_fit(f=damping_envelope_function, 
                  xdata=self.time_scatter_values,
                  ydata=self.amplitude_scatter_values, 
                  p0=self.initial_parameters_guesses.to_list(), 
                  bounds=self.get_parameter_bounds())

        self.solved_parameters = DampingEnvelopeCurveParameters(*list_of_solved_parameters)


