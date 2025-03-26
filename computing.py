from typing import Optional
from matplotlib.collections import PathCollection
import numpy as np
from numpy.typing import ArrayLike
from pandas.core.api import DataFrame
from scipy.optimize import curve_fit
import pandas as pd
import scipy.io.wavfile as wav
import scipy.fftpack as fft
import logging
from scipy.signal import find_peaks

logging.basicConfig(level=logging.INFO)

# Curve to fit
def damping_envelope_function(
    t_i: float | list[float],
    t_offset: float,
    a_offset: float,
    zeta_omega_n: float,
    a_0: float,
) -> float | list[float]:

    if isinstance(t_i, list):
        return [a_0 * np.exp(-zeta_omega_n * (t - t_offset)) + a_offset for t in t_i]
    else:
        return a_0 * np.exp(-zeta_omega_n * (t_i - t_offset)) + a_offset


def compute_fft_from_wav_file(
    wav_filepath: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    """Reads a WAV file and computes its FFT."""
    sample_rate, amplitude_data = wav.read(wav_filepath)
    if len(amplitude_data.shape) > 1:
        amplitude_data = amplitude_data[:, 0]  # Convert stereo to mono

    N: int = len(amplitude_data)
    T: float = 1.0 / sample_rate
    magnitude_data: np.ndarray = fft.fft(amplitude_data) / N
    freq_data: np.ndarray = np.fft.fftfreq(N, T)
    time_data: np.ndarray = np.linspace(0.0, N / sample_rate, N)

    positive_freq_indices = freq_data > 0
    magnitude_data = magnitude_data[positive_freq_indices]
    freq_data= freq_data[positive_freq_indices]

    # TESTS peak detection
    peak_threshold_ratio: float = 0.01
    threshold_magnitude: float = peak_threshold_ratio * np.max(magnitude_data)
    samples_width = int(0.005*N) #harcoded for now
    peak_indices, properties = find_peaks(x=magnitude_data, height=threshold_magnitude, distance=samples_width)

    peak_magnitudes = np.abs(magnitude_data[peak_indices])
    
    sorted_peak_indices = peak_indices[np.argsort(-peak_magnitudes)]
    sorted_peak_frequencies = freq_data[np.array(sorted_peak_indices)]
    sorted_peak_magnitudes = peak_magnitudes[np.argsort(-peak_magnitudes)]

    logging.info(f"Samples width = {samples_width}")

    for i in range(len(sorted_peak_frequencies)):
        logging.info(f"peak {i} = {sorted_peak_frequencies[i]:.1f}Hz at mag. = {sorted_peak_magnitudes[i]}")

    return (time_data, amplitude_data, freq_data, magnitude_data, N)


class DampingEnvelopeCurveParameters:
    a_0: float
    zeta_omega_n: float
    t_offset: float
    a_offset: float

    def __init__(
            self, t_offset: float, a_offset: float, zeta_omega_n: float, a_0: float
    ) -> None:
        self.a_0 = a_0
        self.zeta_omega_n = zeta_omega_n
        self.t_offset = t_offset
        self.a_offset = a_offset

    def to_ndarray(self) -> np.ndarray:
        return np.array(
            [self.t_offset, self.a_offset, self.zeta_omega_n, self.a_0], dtype=float
        )

    def to_tuple(self) -> tuple[float, float, float, float]:
        # return (self.t_offset, self.a_offset, self.zeta_omega_n, self.a_0)
        return tuple(self.to_ndarray())

    def to_list(self) -> list[float]:
        return self.to_ndarray().astype(float).tolist()

    def __str__(self) -> str:

        return f"Curve parameters: zeta_omega_n={self.zeta_omega_n}, a_0={self.a_0}, a_offset={self.a_offset}, t_offset={self.t_offset}."


class DampingEnvelopeCurveFitter:

    time_domain_scatter_data: Optional[PathCollection]
    initial_parameters_guesses: Optional[DampingEnvelopeCurveParameters]
    solved_parameters: Optional[DampingEnvelopeCurveParameters]
    lower_bounds: Optional[DampingEnvelopeCurveParameters]
    upper_bounds: Optional[DampingEnvelopeCurveParameters]

    def __init__(self):
        self.time_domain_scatter_data = None  # Initialize as None
        self.initial_parameters_guesses = None
        self.solved_parameters = None
        self.lower_bounds = None
        self.upper_bounds = None

    @property
    def time_scatter_values(self) -> np.ndarray:
        """Ensures that the scatter points are sorted in ascending order."""
        if self.time_domain_scatter_data is None:
            return np.array([])

        offsets = np.asarray(self.time_domain_scatter_data.get_offsets())
        if offsets.size == 0:
            return np.array([])

        sorted_indices = np.argsort(offsets[:, 0])  # Sort by time values
        return offsets[sorted_indices, 0]  # Return sorted time values

    @property
    def amplitude_scatter_values(self) -> np.ndarray:
        """Returns amplitude values sorted in the same order as time_scatter_values."""
        if self.time_domain_scatter_data is None:
            return np.array([])  # Return empty array if no data

        offsets = np.asarray(self.time_domain_scatter_data.get_offsets())
        if offsets.size == 0:
            return np.array([])

        sorted_indices = np.argsort(offsets[:, 0])  # Sort by time values
        return offsets[sorted_indices, 1]  # Return amplitudes sorted in time order

    @property
    def approximated_amplitude_scatter_values(self) -> np.ndarray:
        approx_amps = damping_envelope_function(
            self.time_scatter_values, *self.solved_parameters.to_list()
        )
        return np.array(approx_amps)

    @property
    def natural_frequency_omega_n(self) -> float:
        return self.get_natural_frequency_omega_n()

    @property
    def natural_freqency_f_n(self) -> float:
        return self.natural_frequency_omega_n / (2 * np.pi)

    @property
    def damped_natural_frequency_omega_d(self) -> float:
        return self.get_damped_natural_frequency_omega_d()

    @property
    def damped_natural_frequency_f_d(self) -> float:
        return self.damped_natural_frequency_omega_d / (2 * np.pi)

    def linearize_time_peaks(self)-> tuple[float, float, float]:
        #offsetting all amplitudes and making sure that the minimum amplitude value is 1 to avoid numerical errors when taking the ln() of values <=0
        a_offset: float = float(np.min(self.amplitude_scatter_values))-1
        t_offset: float = float(np.min(self.time_scatter_values))

        logging.info(f"a_offset = {a_offset:.1f}, t_offset = {t_offset}")

        y: np.ndarray = np.log(self.amplitude_scatter_values - a_offset)
        x: np.ndarray = (self.time_scatter_values - t_offset)
        m: float
        b: float

        coeffs, residuals, rank, _, _ = np.polyfit(x, y, 1, full=True)
        
        # getting slope and intercept
        m = coeffs[0]
        b = coeffs[1]

        # checking rank is good
        if rank != 2:
            logging.warning(f"Rank of the polyfit for a linear regression should be 2 and right now it is = {rank}.")

        # computing R²
        # total sum of squares
        y_mean: float = float(np.mean(y))
        ss_tot: float = np.sum((y - y_mean)**2)

        # residual sum of squares
        ss_res = residuals[0] if residuals.size > 0 else 0

        # Coefficient_of_determination
        r_squared: float = 1 - (ss_res/ss_tot)
        
        return m, b, r_squared
        

    def guess_initial_t_offset(self) -> float:
        # t_offset guess is based on the minimal t value from the data set.
        # it could be more or less, but this will give us an valid order
        return np.min(self.time_scatter_values)

    def guess_initial_A_offset(self) -> float:
        # We want our curve to meet 0 at t -> inf. so our first guess for A_offset is
        # the minimal value of a_i_data. Since a_i_data are the peaks of the time series
        # it is expected that is is over 0.
        return np.min(self.amplitude_scatter_values)

    def guess_initial_amplitude(self) -> float:
        # A_0 is supposed to be the amplitude a t=0. The only thing we know is that it is probably
        # greater than the shifted max we have in a_i_data.
        return np.max(self.amplitude_scatter_values) - np.min(
            self.amplitude_scatter_values
        )

    def guess_initial_natural_frequency_omega_n(self) -> float:
        # Our best guess at thhis point is the measured damped frequency
        return self.get_damped_natural_frequency_omega_d()

    def guess_initial_zeta_omega_n(self, zeta_guess: float = 0.03) -> float:

        # This one we have to build gradually the compounded value.
        omega_n_guess: float = self.guess_initial_natural_frequency_omega_n()
        # zeta_guess is harcoded here but generally it is expected to be between
        # 1% and 5% for metalic structures

        return zeta_guess * omega_n_guess

    def guess_initial_parameters(self):
        # the order of parameters must fit damping_envelope_curve()
        t_offset_guess = self.guess_initial_t_offset()
        a_offset_guess = self.guess_initial_A_offset()
        a_0_guess = self.guess_initial_amplitude()
        zeta_omega_n_guess = self.guess_initial_zeta_omega_n()

        self.initial_parameters_guesses = DampingEnvelopeCurveParameters(
            a_0=a_0_guess,
            zeta_omega_n=zeta_omega_n_guess,
            t_offset=t_offset_guess,
            a_offset=a_offset_guess,
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
            a_offset=a_offset_min,
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
            a_offset=a_offset_max,
        )

    def get_parameter_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        self.compute_lower_bounds()
        self.compute_upper_bounds()
        return (self.lower_bounds.to_ndarray(), self.upper_bounds.to_ndarray())

    def get_coefficient_of_determination(self) -> float:
        # TODO: make sure solved parameters exists
        # get predicted values of A(i) using solved parameters
        a_predicted: float = damping_envelope_function(
            self.time_scatter_values, *self.solved_parameters.to_list()
        )
        # get the mean value of the actual data
        a_i_mean: float = float(np.mean(self.amplitude_scatter_values))

        ss_res: float = np.sum((self.amplitude_scatter_values - a_predicted) ** 2)
        ss_tot: float = np.sum((self.amplitude_scatter_values - a_i_mean) ** 2)

        r_squared: float = 1 - (ss_res / ss_tot)

        return r_squared

    def get_damped_natural_frequency_omega_d(self) -> float:

        # we can measure the damped frequency by evaluating the mean intervals in t_i_data
        t_invervals: np.ndarray = np.diff(self.time_scatter_values)
        tau_mean_period: float = float(np.mean(t_invervals))
        mean_damped_frequency: float = 2 * np.pi / tau_mean_period

        return mean_damped_frequency

    def get_natural_frequency_omega_n(self) -> float:

        if self.solved_parameters is not None:

            omega_d: float = self.get_damped_natural_frequency_omega_d()
            zeta_omega_n: float = self.solved_parameters.zeta_omega_n

            # TODO: test for solved parameters first
            term1: float = (omega_d) ** 2
            term2: float = zeta_omega_n**2
            return np.sqrt(term1 + term2)

        else:
            return 0.0

    def get_damping_ratio_zeta(self) -> float:
        if self.solved_parameters is not None:
            omega_d: float = self.get_damped_natural_frequency_omega_d()
            omega_n: float = self.get_natural_frequency_omega_n()

            term1: float = (omega_d / omega_n) ** 2
            return np.sqrt(1 - term1)
        else:
            return 0.0

    def curve_fit_wrapper(self, t, t_offset, a_offset, zeta_omega_n, a_0):
        return damping_envelope_function(t, t_offset, a_offset, zeta_omega_n, a_0)

    def solve(self):
        """Attempts to solve for damping parameters, handling failures gracefully."""
        if len(self.time_scatter_values) < 5:
            print("Not enough data points to solve for curve fit.")
            return
        
        m: float
        b: float
        r_squared: float

        m, b, r_squared = self.linearize_time_peaks()
        print(f"m = {m:.2f}, b = {b:.2f} and R² = {r_squared:.3f}")

        self.guess_initial_parameters()

        print("\n=== Initial Guesses ===")
        print(f"  a_0 = {self.initial_parameters_guesses.a_0}")
        print(f"  zeta_omega_n = {self.initial_parameters_guesses.zeta_omega_n}")
        print(f"  t_offset = {self.initial_parameters_guesses.t_offset}")
        print(f"  a_offset = {self.initial_parameters_guesses.a_offset}")
        print("=========================")

        try:
            # Verify correct order of parameters
            list_of_solved_parameters, _ = curve_fit(damping_envelope_function,
                xdata=self.time_scatter_values,
                ydata=self.amplitude_scatter_values,
                p0=self.initial_parameters_guesses.to_list(),
                bounds=self.get_parameter_bounds(),
                maxfev=5000,
            )

            print(f"List of solved parameters{list_of_solved_parameters}")
            
            # TODO: orders of parameters can be problematic if there is refactoring
            self.solved_parameters = DampingEnvelopeCurveParameters(
                *list_of_solved_parameters
            )

            print("\n=== Fitted Parameters ===")
            print(f"  a_0 = {self.solved_parameters.a_0}")
            print(f"  zeta_omega_n = {self.solved_parameters.zeta_omega_n}")
            print(f"  t_offset = {self.solved_parameters.t_offset}")
            print(f"  a_offset = {self.solved_parameters.a_offset}")
            print("=========================")

            # Check for extreme damping values
            if (
                self.solved_parameters.zeta_omega_n < 0
                or self.solved_parameters.zeta_omega_n > 10
            ):
                print("Warning: Unusually high or negative damping detected.")

        except RuntimeError as e:
            print("Curve fitting failed:", e)
            self.solved_parameters = None
