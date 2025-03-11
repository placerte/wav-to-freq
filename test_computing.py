from computing import *

# Read the file
filepath: str = "hit2-1_time_scatter_points.csv"
t_i_data, a_i_data = read_data_file(filepath)

# Set the initial parameters guesses to help the solver
initial_parameter_guesses: list[float] = guess_initial_parameters(t_i_data, a_i_data)

# Set lower and upper bounds to help the solver
parameter_bounds: tuple[np.ndarray, np.ndarray] = get_parameter_bounds(a_i_data)

# fit the custom function to the data
solved_parameters, _ = curve_fit(custom_curve, t_i_data, a_i_data, p0=initial_parameter_guesses, bounds=parameter_bounds)

# Calculate the Coefficientof Determination
r_squared = get_coefficient_of_determination(t_i_data, a_i_data, solved_parameters)

# Get natural frequencies and damping ratio
fd: float = get_damped_natural_frequency_fd(t_i_data)
fn: float = get_natural_frequency_fn(fd, solved_parameters)
zeta: float = get_damping_ratio_zeta(fd, fn)

print_solved_parameters(solved_parameters)
print(f"Coefficient of Determination: R²={r_squared}")
print(f"Damped natural frequency, fd={fd} | natural frequency, fn={fn} | damping ratio, zeta={zeta}")
