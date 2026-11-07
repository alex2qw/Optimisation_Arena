import time

import numpy as np

from app.problems.base import BaseProblem
from app.schemas import GradientDescentParameters

from .base import ALGORITHM_NAMES, AlgorithmResult, Evaluator, EvaluationBudgetExceeded, TrajectoryPoint, _validate_bounds


def run_gradient_descent(problem: BaseProblem, bounds, start: np.ndarray, iterations: int, seed: int, params: GradientDescentParameters, max_evaluations: int) -> AlgorithmResult:
    started = time.perf_counter()
    low, high = _validate_bounds(bounds)
    current = np.clip(np.asarray(start, dtype=float), low, high)
    evaluator = Evaluator(problem, max_evaluations)
    trajectory: list[TrajectoryPoint] = []
    best_position = current.copy()
    best_score = None
    status, reason, error = "completed", "iteration budget reached", None
    stagnant = 0
    try:
        current_score = evaluator(current)
        best_score = current_score
        trajectory.append(TrajectoryPoint(0, current.tolist(), current_score, best_position.tolist(), best_score, evaluator.count))
        for iteration in range(1, iterations + 1):
            gradient = np.asarray(problem.gradient(current), dtype=float)
            gradient_norm = float(np.linalg.norm(gradient))
            if not np.all(np.isfinite(gradient)):
                status, reason = "failed", "non-finite gradient detected"
                error = reason
                break
            if gradient_norm <= params.tolerance:
                status, reason = "early_stopped", "gradient norm met convergence tolerance"
                trajectory.append(TrajectoryPoint(iteration, current.tolist(), current_score, best_position.tolist(), best_score, evaluator.count))
                break
            step = float(params.learning_rate)
            candidate = current.copy()
            candidate_score = current_score
            improved = False
            for _ in range(25):
                candidate = np.clip(current - step * gradient, low, high)
                candidate_score = evaluator(candidate)
                if candidate_score < current_score - params.tolerance:
                    improved = True
                    break
                step *= 0.5
            if not improved:
                stagnant += 1
            else:
                stagnant = 0
                current, current_score = candidate, candidate_score
            if current_score < best_score:
                best_score, best_position = current_score, current.copy()
            trajectory.append(TrajectoryPoint(iteration, current.tolist(), current_score, best_position.tolist(), best_score, evaluator.count))
            if stagnant >= params.patience:
                status, reason = "early_stopped", "no meaningful improvement during patience window"
                break
        else:
            status, reason = "completed", "iteration budget reached"
    except EvaluationBudgetExceeded as exc:
        status, reason, error = "early_stopped", "function-evaluation budget reached", str(exc)
    except (FloatingPointError, ValueError, OverflowError) as exc:
        status, reason, error = "failed", "numerical failure", str(exc)
    return AlgorithmResult("gradient_descent", ALGORITHM_NAMES["gradient_descent"], status, best_position.tolist() if best_score is not None else None, float(best_score) if best_score is not None else None, trajectory, evaluator.count, max(0, len(trajectory) - 1), (time.perf_counter() - started) * 1000, seed, params.model_dump(), reason, {"gradient_norm_final": float(np.linalg.norm(problem.gradient(current))) if np.all(np.isfinite(problem.gradient(current))) else None, "stagnant_steps": stagnant}, error)
