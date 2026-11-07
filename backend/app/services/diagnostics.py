from typing import Any

import numpy as np


def _finite_position(value: Any) -> np.ndarray | None:
    try:
        position = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if position.shape != (2,) or not np.all(np.isfinite(position)):
        return None
    return position


def diagnose_result(result: dict[str, Any], known_minima: list[tuple[float, float]], tolerance: float = 1e-2) -> dict[str, Any]:
    raw_scores = list(result.get("scores", []))
    raw_best_scores = list(result.get("best_so_far", []))
    finite_scores = [float(value) for value in raw_scores if isinstance(value, (int, float)) and np.isfinite(value)]
    finite_best_scores = [float(value) for value in raw_best_scores if isinstance(value, (int, float)) and np.isfinite(value)]
    initial = finite_scores[0] if finite_scores else None
    best_value = result.get("best_score")
    best = float(best_value) if isinstance(best_value, (int, float)) and np.isfinite(best_value) else None
    improvement = (initial - best) if initial is not None and best is not None else None
    meaningful_delta = max(abs(initial or 0.0) * 1e-10, 1e-12)
    relative = None if initial in (None, 0) or best is None else improvement / abs(initial)
    improvement_observed = improvement is not None and improvement > meaningful_delta

    if len(finite_best_scores) >= 2:
        meaningful_indices = [index for index in range(1, len(finite_best_scores)) if finite_best_scores[index] < finite_best_scores[index - 1] - meaningful_delta]
        last_improvement = meaningful_indices[-1] if meaningful_indices else 0
        stagnation_steps = len(finite_best_scores) - 1 - last_improvement
        stagnation_observed = stagnation_steps >= max(5, len(finite_best_scores) // 10)
    else:
        stagnation_steps = 0
        stagnation_observed = False

    termination_reason = str(result.get("termination_reason", ""))
    reason_lower = termination_reason.lower()
    if "gradient norm" in reason_lower:
        termination_category = "convergence_tolerance"
    elif "temperature" in reason_lower:
        termination_category = "temperature_floor"
    elif "patience" in reason_lower or "meaningful improvement" in reason_lower:
        termination_category = "stagnation_patience"
    elif "evaluation" in reason_lower:
        termination_category = "evaluation_budget"
    elif "iteration budget" in reason_lower or "generation budget" in reason_lower:
        termination_category = "iteration_budget"
    elif "numerical" in reason_lower or result.get("status") == "failed":
        termination_category = "numerical_failure"
    else:
        termination_category = "other"

    position = _finite_position(result.get("best_position"))
    distances = [float(np.linalg.norm(position - np.asarray(point, dtype=float))) for point in known_minima] if position is not None else []
    nearest = min(distances) if distances else None
    target_attained = nearest is not None and nearest <= tolerance and best is not None and best <= 1e-4
    execution_succeeded = result.get("status") in {"completed", "early_stopped"} and best is not None
    if not execution_succeeded:
        optimization_status = "failed"
    elif target_attained:
        optimization_status = "target_attained"
    elif improvement_observed:
        optimization_status = "improved"
    else:
        optimization_status = "no_improvement"

    return {
        "initial_score": initial,
        "improvement": improvement,
        "relative_improvement": relative,
        "improvement_observed": improvement_observed,
        "iterations_since_meaningful_improvement": stagnation_steps,
        "stagnation_observed": stagnation_observed,
        "stagnation_status": "observed" if stagnation_observed else ("not_observed" if len(finite_best_scores) >= 2 else "not_assessable"),
        "non_finite_observed": len(finite_scores) != len(raw_scores) or len(finite_best_scores) != len(raw_best_scores),
        "stopping_criterion_met": result.get("status") in {"completed", "early_stopped"} and termination_category not in {"iteration_budget", "generation_budget"},
        "termination_category": termination_category,
        "nearest_global_minimum_distance": nearest,
        "target_attained": target_attained,
        "reached_known_optimum": target_attained,
        "optimization_status": optimization_status,
        "optimization_success": execution_succeeded and (improvement_observed or target_attained),
        "execution_succeeded": execution_succeeded,
        "observable_note": "A flat best-so-far history indicates no measured improvement; a local-minimum explanation remains a hypothesis." if stagnation_observed else "No configured stagnation threshold was observed in the recorded history.",
    }


def trial_statistics(scores: list[float], execution_successes: list[bool], target_attainments: list[bool] | None = None) -> dict[str, Any]:
    values = np.asarray([value for value in scores if np.isfinite(value)], dtype=float)
    trial_count = len(execution_successes)
    return {
        "median_score": float(np.median(values)) if values.size else None,
        "score_spread": float(np.std(values)) if values.size else None,
        "success_rate": (float(np.mean(execution_successes)) if trial_count > 1 else None),
        "target_attainment_rate": (float(np.mean(target_attainments)) if target_attainments is not None and trial_count > 1 else None),
    }
