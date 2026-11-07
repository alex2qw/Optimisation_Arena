import time

import numpy as np

from app.problems.base import BaseProblem
from app.schemas import GeneticAlgorithmParameters

from .base import ALGORITHM_NAMES, AlgorithmResult, Evaluator, EvaluationBudgetExceeded, TrajectoryPoint, _validate_bounds


def run_genetic_algorithm(problem: BaseProblem, bounds, start: np.ndarray, iterations: int, seed: int, params: GeneticAlgorithmParameters, max_evaluations: int, include_population_snapshots: bool = False) -> AlgorithmResult:
    started = time.perf_counter()
    rng = np.random.default_rng(seed)
    low, high = _validate_bounds(bounds)
    population = rng.uniform(low, high, size=(params.population_size, 2))
    population[0] = np.clip(start, low, high)
    evaluator = Evaluator(problem, max_evaluations)
    trajectory: list[TrajectoryPoint] = []
    snapshots: list[list[list[float]]] | None = [] if include_population_snapshots else None
    best_position = None
    best_score = None
    status, reason, error = "completed", "generation budget reached", None
    diversity = 0.0
    try:
        for generation in range(iterations + 1):
            scores = np.array([evaluator(member) for member in population], dtype=float)
            order = np.argsort(scores)
            population, scores = population[order], scores[order]
            if best_score is None or scores[0] < best_score:
                best_score, best_position = float(scores[0]), population[0].copy()
            diversity = float(np.mean(np.linalg.norm(population - np.mean(population, axis=0), axis=1)))
            trajectory.append(TrajectoryPoint(generation, population[0].tolist(), float(scores[0]), best_position.tolist(), float(best_score), evaluator.count))
            if snapshots is not None:
                snapshots.append(population.tolist())
            if generation == iterations:
                break
            elites = population[:params.elite_count].copy()
            next_population = [member for member in elites]
            while len(next_population) < params.population_size:
                indices = rng.integers(0, max(params.tournament_size, 2), size=2)
                parent_a = population[indices[np.argmin(scores[indices])]]
                indices = rng.integers(0, max(params.tournament_size, 2), size=2)
                parent_b = population[indices[np.argmin(scores[indices])]]
                alpha = rng.random()
                child = alpha * parent_a + (1 - alpha) * parent_b
                mutation_mask = rng.random(2) < params.mutation_rate
                child = child + mutation_mask * rng.normal(0, params.mutation_strength, size=2)
                next_population.append(np.clip(child, low, high))
            population = np.asarray(next_population, dtype=float)
    except EvaluationBudgetExceeded as exc:
        status, reason, error = "early_stopped", "function-evaluation budget reached", str(exc)
    except (FloatingPointError, ValueError, OverflowError) as exc:
        status, reason, error = "failed", "numerical failure", str(exc)
    return AlgorithmResult("genetic_algorithm", ALGORITHM_NAMES["genetic_algorithm"], status, best_position.tolist() if best_position is not None else None, float(best_score) if best_score is not None else None, trajectory, evaluator.count, max(0, len(trajectory) - 1), (time.perf_counter() - started) * 1000, seed, params.model_dump(), reason, {"population_diversity_final": diversity, "population_snapshots_included": include_population_snapshots}, error, snapshots)
