from dataclasses import asdict, dataclass, field
from typing import Any, Callable

import numpy as np

from app.problems.base import BaseProblem
from app.schemas import GeneticAlgorithmParameters, GradientDescentParameters, SimulatedAnnealingParameters

ALGORITHM_NAMES = {
    "gradient_descent": "Gradient Descent",
    "simulated_annealing": "Simulated Annealing",
    "genetic_algorithm": "Genetic Algorithm",
}


@dataclass
class TrajectoryPoint:
    iteration: int
    position: list[float]
    score: float
    best_position: list[float]
    best_score: float
    function_evaluations: int


@dataclass
class AlgorithmResult:
    algorithm: str
    display_name: str
    status: str
    best_position: list[float] | None
    best_score: float | None
    trajectory: list[TrajectoryPoint] = field(default_factory=list)
    function_evaluations: int = 0
    iterations_completed: int = 0
    runtime_ms: float = 0.0
    effective_seed: int = 0
    parameters: dict[str, Any] = field(default_factory=dict)
    termination_reason: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    population_snapshots: list[Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvaluationBudgetExceeded(RuntimeError):
    pass


class Evaluator:
    def __init__(self, problem: BaseProblem, limit: int):
        self.problem = problem
        self.limit = limit
        self.count = 0

    def __call__(self, point: np.ndarray) -> float:
        if self.count >= self.limit:
            raise EvaluationBudgetExceeded("maximum objective-evaluation budget reached")
        score = float(self.problem.objective(point))
        self.count += 1
        if not np.isfinite(score):
            raise FloatingPointError("objective returned a non-finite value")
        return score


def get_algorithm_metadata() -> list[dict[str, Any]]:
    return [
        {"identifier": "gradient_descent", "name": ALGORITHM_NAMES["gradient_descent"], "description": "Uses analytical gradients with backtracking line search.", "parameters": {"learning_rate": {"default": 0.01, "min": 1e-8, "max": 10}, "tolerance": {"default": 1e-8, "min": 1e-12, "max": 1}, "patience": {"default": 30, "min": 1, "max": 1000}}, "required_inputs": ["analytical gradient", "starting point"]},
        {"identifier": "simulated_annealing", "name": ALGORITHM_NAMES["simulated_annealing"], "description": "Explores with temperature-dependent acceptance of worse candidates.", "parameters": {"initial_temperature": {"default": 10.0, "min": 1e-8, "max": 1e8}, "cooling_rate": {"default": 0.99, "min": 1e-8, "max": 0.999999}, "proposal_scale": {"default": 0.5, "min": 1e-8, "max": 100}, "min_temperature": {"default": 1e-8, "min": 1e-12, "max": 1}}, "required_inputs": ["starting point"]},
        {"identifier": "genetic_algorithm", "name": ALGORITHM_NAMES["genetic_algorithm"], "description": "Population search with tournament selection, crossover, mutation and elitism.", "parameters": {"population_size": {"default": 50, "min": 4, "max": 500}, "mutation_rate": {"default": 0.1, "min": 0, "max": 1}, "mutation_strength": {"default": 0.2, "min": 1e-8, "max": 10}, "elite_count": {"default": 2, "min": 1, "max": 100}}, "required_inputs": ["bounds"]},
    ]


def _validate_bounds(bounds: tuple[tuple[float, float], tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    low = np.array([bounds[0][0], bounds[1][0]], dtype=float)
    high = np.array([bounds[0][1], bounds[1][1]], dtype=float)
    return low, high


def run_algorithm(name: str, problem: BaseProblem, bounds, start: np.ndarray, iterations: int, seed: int, parameters: dict[str, Any], max_evaluations: int, include_population_snapshots: bool = False) -> AlgorithmResult:
    from .genetic_algorithm import run_genetic_algorithm
    from .gradient_descent import run_gradient_descent
    from .simulated_annealing import run_simulated_annealing

    if name == "gradient_descent":
        parsed = GradientDescentParameters.model_validate(parameters)
        return run_gradient_descent(problem, bounds, start, iterations, seed, parsed, max_evaluations)
    if name == "simulated_annealing":
        parsed = SimulatedAnnealingParameters.model_validate(parameters)
        return run_simulated_annealing(problem, bounds, start, iterations, seed, parsed, max_evaluations)
    if name == "genetic_algorithm":
        parsed = GeneticAlgorithmParameters.model_validate(parameters)
        return run_genetic_algorithm(problem, bounds, start, iterations, seed, parsed, max_evaluations, include_population_snapshots)
    raise ValueError(f"Unsupported algorithm: {name}")
