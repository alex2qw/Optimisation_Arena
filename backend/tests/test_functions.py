import numpy as np
import pytest

from app.problems import list_problems


@pytest.mark.parametrize("identifier,point", [("sphere", (0, 0)), ("rosenbrock", (1, 1)), ("rastrigin", (0, 0)), ("himmelblau", (3, 2)), ("himmelblau", (-2.805118, 3.131312)), ("himmelblau", (-3.779310, -3.283186)), ("himmelblau", (3.584428, -1.848126))])
def test_known_minima(identifier, point):
    problem = next(item for item in list_problems() if item.identifier == identifier)
    assert problem.objective(point) == pytest.approx(0, abs=1e-3)


def test_functions_are_finite_on_default_grid():
    for problem in list_problems():
        low, high = problem.default_bounds
        values = problem.vectorized_objective(np.linspace(low, high, 11)[:, None], np.linspace(low, high, 11)[None, :])
        assert values.shape == (11, 11)
        assert np.isfinite(values).all()


def test_gradients_match_finite_difference():
    for problem in list_problems():
        point = np.array([0.37, -0.41])
        analytical = problem.gradient(point)
        numerical = np.zeros(2)
        step = 1e-6
        for index in range(2):
            plus, minus = point.copy(), point.copy()
            plus[index] += step
            minus[index] -= step
            numerical[index] = (problem.objective(plus) - problem.objective(minus)) / (2 * step)
        assert analytical == pytest.approx(numerical, rel=1e-5, abs=1e-5)
