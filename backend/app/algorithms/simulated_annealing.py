import math
import time

import numpy as np

from app.problems.base import BaseProblem
from app.schemas import SimulatedAnnealingParameters

from .base import ALGORITHM_NAMES, AlgorithmResult, Evaluator, EvaluationBudgetExceeded, TrajectoryPoint, _validate_bounds


def run_simulated_annealing(problem: BaseProblem, bounds, start: np.ndarray, iterations: int, seed: int, params: SimulatedAnnealingParameters, max_evaluations: int) -> AlgorithmResult:
    started = time.perf_counter()
    rng = np.random.default_rng(seed)
    low, high = _validate_bounds(bounds)
    current = np.clip(np.asarray(start, dtype=float), low, high)
    evaluator = Evaluator(problem, max_evaluations)
    trajectory: list[TrajectoryPoint] = []
    best_position = current.copy()
    best_score = None
    temperature = params.initial_temperature
    accepted_worse = 0
    status, reason, error = "completed", "iteration budget reached", None
    try:
        current_score = evaluator(current)
        best_score = current_score
        trajectory.append(TrajectoryPoint(0, current.tolist(), current_score, best_position.tolist(), best_score, evaluator.count))
        for iteration in range(1, iterations + 1):
            proposal = np.clip(current + rng.normal(0, params.proposal_scale, size=2), low, high)
            proposal_score = evaluator(proposal)
            delta = proposal_score - current_score
            accepted = delta <= 0 or rng.random() < math.exp(-delta / max(temperature, 1e-12))
            if accepted:
                if delta > 0:
                    accepted_worse += 1
                current, current_score = proposal, proposal_score
            if current_score < best_score:
                best_score, best_position = current_score, current.copy()
            trajectory.append(TrajectoryPoint(iteration, current.tolist(), current_score, best_position.tolist(), best_score, evaluator.count))
            temperature *= params.cooling_rate
            if temperature <= params.min_temperature:
                status, reason = "early_stopped", "temperature reached minimum"
                break
        else:
            status, reason = "completed", "iteration budget reached"
    except EvaluationBudgetExceeded as exc:
        status, reason, error = "early_stopped", "function-evaluation budget reached", str(exc)
    except (FloatingPointError, ValueError, OverflowError) as exc:
        status, reason, error = "failed", "numerical failure", str(exc)
    return AlgorithmResult("simulated_annealing", ALGORITHM_NAMES["simulated_annealing"], status, best_position.tolist() if best_score is not None else None, float(best_score) if best_score is not None else None, trajectory, evaluator.count, max(0, len(trajectory) - 1), (time.perf_counter() - started) * 1000, seed, params.model_dump(), reason, {"final_temperature": temperature, "accepted_worse_moves": accepted_worse}, error)
