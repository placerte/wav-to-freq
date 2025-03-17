import matplotlib.pyplot as plt
from computing import DampingEnvelopeCurveFitter, DampingEnvelopeCurveParameters, damping_envelope_function
import pytest
import logging

logging.basicConfig(level=logging.INFO, force=True)

# Define test input values
t_i_values = [
    0.013,
    0.013868642,
    0.014796183,
    0.015786607,
    0.017044289,
    0.017987551,
    0.018993697,
    0.020235658,
    0.021257525,
    0.022122181,
    0.023301258,
    0.024307404,
    0.025257727,
    0.026277649,
    0.027494975,
    0.028514897,
    0.029501918,
    0.030390237,
    0.031739166,
    0.032462982,
    0.033482904,
    0.03470023,
    0.035720152,
    0.036937478,
    0.037924499,
    0.03887862,
    0.039865641,
    0.04121457,
    0.042037087,
    0.04308991,
    0.044109832,
    0.045294257,
    0.046083874,
    0.047169598,
    0.04822242,
    0.049275243,
]

a_i_values= [
    18136.01954,
    16218.18814,
    16164.91504,
    14140.53745,
    10731.05939,
    9345.958933,
    10358.14773,
    7907.585379,
    8493.589419,
    5723.3885,
    7747.766095,
    5243.930649,
    4980.425781,
    2580.762236,
    3605.861226,
    4444.578582,
    2743.846166,
    647.0527772,
    1392.579316,
    437.3734383,
    181.0986908,
    157.8009865,
    -354.7485086,
    -284.8553957,
    -168.3668741,
    -191.6645784,
    -191.6645784,
    -261.5576913,
    -424.6416216,
    -587.7255518,
    -634.3209605,
    -774.1071864,
    -890.595708,
    -1053.679638,
    -1170.16816,
    -1263.358977
]

parameters = (0.01224, -2046.8, 92.71, 21737.76)

a_i_expected = [
    18212.03998,
    16644.52369,
    15104.38304,
    13599.6629,
    11877.63437,
    10711.6702,
    9575.383114,
    8311.347335,
    7375.093953,
    6649.292804,
    5748.816514,
    5054.528076,
    4455.639032,
    3868.962411,
    3237.615824,
    2760.834235,
    2340.431481,
    1993.594459,
    1518.624505,
    1287.218003,
    986.4092751,
    662.6967607,
    418.2348912,
    155.1595243,
    -37.39044973,
    -207.5011976,
    -368.3383669,
    -565.6504989,
    -674.3974849,
    -802.0238909,
    -914.3326779,
    -1032.102394,
    -1103.729978,
    -1194.035754,
    -1273.338462,
    -1345.266424,
]


@pytest.fixture
def mock_solved_curve_parameters() -> DampingEnvelopeCurveParameters:
    return DampingEnvelopeCurveParameters(
        t_offset=0.01224, a_offset=-2046.8, zeta_omega_n=92.71, a_0=21737.76
    )


# ✅ Fix: Parametrize Correctly (individual cases)
@pytest.mark.parametrize("t_i, expected", zip(t_i_values, a_i_expected))
def test_damping_envelope_function_parametrized(t_i, expected):
    a_test: float | list[float] = damping_envelope_function(t_i, *parameters)
    assert isinstance(a_test, float)
    assert a_test == pytest.approx(expected, rel=1e-2)


# ✅ Fix: Single Test for Full Curve
def test_damping_envelope_function_parametrized_full_curve():
    a_test: float| list[float] = damping_envelope_function(t_i_values, *parameters)

    assert isinstance(a_test, list)  # Ensure output is a list
    assert len(a_test) == len(a_i_expected)  # Ensure length matches input size
    assert a_test == pytest.approx(a_i_expected, rel=1e-2)  # Compare values


@pytest.mark.parametrize(
    "t_i, parameters, expected",
    [
        (0.032, (0.01224, -2046.8, 92.71, 21737.76), 1433.44),  # Case tuple
        (0.032, [0.01224, -2046.8, 92.71, 21737.76], 1433.44),  # Case list
        (0.05, (0.01, 1000, 100, 20000), 1366.31),  # Case tuple 2
    ],
)
def test_damping_envelope_function_variations(t_i, parameters, expected):
    a_test: float | list[float] = damping_envelope_function(t_i, *parameters)
    assert isinstance(a_test, float)
    assert a_test == pytest.approx(expected, rel=1e-2)


def test_damping_envelope_function_from_object_parameters(
    mock_solved_curve_parameters: DampingEnvelopeCurveParameters,
):
    t_i: float = 0.032
    a_test: float | list[float] = damping_envelope_function(
        t_i, *mock_solved_curve_parameters.to_list()
    )
    assert isinstance(a_test, float)
    assert a_test == pytest.approx(1433.44, rel=1e-2)

def test_solving_parameters():
    
    fitter: DampingEnvelopeCurveFitter = DampingEnvelopeCurveFitter()
    fitter.time_domain_scatter_data = plt.scatter(x=t_i_values, y=a_i_values)
    fitter.solve()

    assert fitter.solved_parameters is not None
    logging.info(f"Solved parameters: {fitter.solved_parameters}")
    assert fitter.solved_parameters.a_0 == pytest.approx(20103, rel=1e-2)
    assert fitter.solved_parameters.a_offset == pytest.approx(-2029, rel=1e-2)
    assert fitter.solved_parameters.t_offset == pytest.approx(0.0131, rel=1e-2)
    assert fitter.solved_parameters.zeta_omega_n == pytest.approx(93.16, rel=1e-2)
