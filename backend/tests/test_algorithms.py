import numpy as np
import pytest

from app.algorithms import run_algorithm
from app.problems import get_problem
from app.schemas import GeneticAlgorithmParameters


def run(name, seed=7):
    problem = get_problem("rastrigin")
    bounds = ((-5.12, 5.12), (-5.12, 5.12))
    params = {"genetic_algorithm": {"population_size": 12, "elite_count": 2}}.get(name, {})
    return run_algorithm(name, problem, bounds, np.array([3.5, -2.5]), 30, seed, params, 2000)


def test_all_algorithms_return_common_finite_results():
    for name in ("gradient_descent", "simulated_annealing", "genetic_algorithm"):
        result = run(name)
        assert result.best_score is not None and np.isfinite(result.best_score)
        assert len(result.best_position) == 2
        assert all(-5.12 <= value <= 5.12 for value in result.best_position)
        assert all(result.trajectory[i].best_score <= result.trajectory[i - 1].best_score + 1e-10 for i in range(1, len(result.trajectory)))
        assert result.function_evaluations == result.trajectory[-1].function_evaluations


def test_stochastic_algorithms_are_reproducible():
    for name in ("simulated_annealing", "genetic_algorithm"):
        first, second = run(name, 11), run(name, 11)
        assert first.best_score == second.best_score
        assert [point.position for point in first.trajectory] == [point.position for point in second.trajectory]


def test_algorithm_changes_from_non_optimal_start():
    result = run("gradient_descent")
    assert result.best_position != [3.5, -2.5]


def test_genetic_algorithm_rejects_oversized_tournament():
    with pytest.raises(ValueError):
        GeneticAlgorithmParameters(population_size=4, tournament_size=5)
