import json
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app import __version__
from app.services.diagnostics import diagnose_result, trial_statistics
from app.services.metrics import fastest_algorithm, select_winner


REQUIRED_REPORT_KEYS = {"schema_version", "experiment_id", "status", "created_at", "config", "problem", "landscape", "results", "animation", "convergence", "comparison", "diagnostics", "overall_summary", "ai_insights", "metadata"}


def _trajectory_dict(result) -> dict[str, Any]:
    points = result.trajectory
    return {
        "path": [point.position for point in points],
        "scores": [point.score for point in points],
        "best_so_far": [point.best_score for point in points],
        "best_so_far_positions": [point.best_position for point in points],
        "iterations": [point.iteration for point in points],
        "function_evaluations": [point.function_evaluations for point in points],
    }


def _validate_trajectory(problem, trajectory: dict[str, Any], bounds: dict[str, tuple[float, float]]) -> None:
    lengths = {key: len(value) for key, value in trajectory.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"trajectory arrays are misaligned: {lengths}")
    for index, (position, score, best_position, best_score, iteration, evaluations) in enumerate(zip(trajectory["path"], trajectory["scores"], trajectory["best_so_far_positions"], trajectory["best_so_far"], trajectory["iterations"], trajectory["function_evaluations"])):
        current = np.asarray(position, dtype=float)
        best = np.asarray(best_position, dtype=float)
        if current.shape != (2,) or best.shape != (2,) or not np.all(np.isfinite(current)) or not np.all(np.isfinite(best)):
            raise ValueError("trajectory contains a non-finite or invalid position")
        if not (bounds["x"][0] <= current[0] <= bounds["x"][1] and bounds["y"][0] <= current[1] <= bounds["y"][1]):
            raise ValueError("trajectory position is outside the selected bounds")
        if not (bounds["x"][0] <= best[0] <= bounds["x"][1] and bounds["y"][0] <= best[1] <= bounds["y"][1]):
            raise ValueError("best-so-far position is outside the selected bounds")
        actual_score = float(problem.objective(current))
        actual_best_score = float(problem.objective(best))
        if not np.isfinite(score) or not np.isfinite(best_score) or not np.isclose(actual_score, score, rtol=1e-8, atol=1e-8) or not np.isclose(actual_best_score, best_score, rtol=1e-8, atol=1e-8):
            raise ValueError(f"trajectory score does not match its recorded position at index {index}")
        if index and (best_score > trajectory["best_so_far"][index - 1] + 1e-10 or iteration <= trajectory["iterations"][index - 1] or evaluations < trajectory["function_evaluations"][index - 1]):
            raise ValueError("trajectory best-so-far, iteration, or evaluation history is invalid")


def validate_report(report: dict[str, Any]) -> dict[str, Any]:
    missing = REQUIRED_REPORT_KEYS - set(report)
    if missing:
        raise ValueError(f"report is missing required keys: {sorted(missing)}")
    try:
        json.dumps(report, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"report is not strict JSON serialisable: {exc}") from exc
    return report


def _result_row(result, problem, bounds, trial_results: list) -> tuple[dict[str, Any], dict[str, Any]]:
    trajectory = _trajectory_dict(result)
    if trajectory["path"]:
        _validate_trajectory(problem, trajectory, bounds)
    diagnostics = {**result.diagnostics, **diagnose_result({**trajectory, "best_position": result.best_position, "best_score": result.best_score, "status": result.status, "termination_reason": result.termination_reason}, list(problem.global_minima))}
    trial_rows = []
    trial_scores = []
    execution_successes = []
    target_attainments = []
    for trial in trial_results:
        trial_trajectory = _trajectory_dict(trial)
        trial_diagnostics = diagnose_result({**trial_trajectory, "best_position": trial.best_position, "best_score": trial.best_score, "status": trial.status, "termination_reason": trial.termination_reason}, list(problem.global_minima))
        if trial_trajectory["path"]:
            _validate_trajectory(problem, trial_trajectory, bounds)
        execution_success = bool(trial_diagnostics["execution_succeeded"])
        target_attained = bool(trial_diagnostics["target_attained"])
        trial_rows.append({"status": trial.status, "execution_status": trial.status, "execution_succeeded": execution_success, "optimization_success": trial_diagnostics["optimization_success"], "target_attained": target_attained, "stagnation_observed": trial_diagnostics["stagnation_observed"], "best_score": trial.best_score, "runtime_ms": trial.runtime_ms, "function_evaluations": trial.function_evaluations, "success": execution_success})
        if trial.best_score is not None and np.isfinite(trial.best_score):
            trial_scores.append(float(trial.best_score))
        execution_successes.append(execution_success)
        target_attainments.append(target_attained)
    stats = trial_statistics(trial_scores, execution_successes, target_attainments)
    row = {
        "algorithm": result.algorithm,
        "display_name": result.display_name,
        "status": result.status,
        "execution_status": result.status,
        "execution_completed": diagnostics["execution_succeeded"],
        "execution_succeeded": diagnostics["execution_succeeded"],
        "optimization_success": diagnostics["optimization_success"],
        "optimization_status": diagnostics["optimization_status"],
        "target_attained": diagnostics["target_attained"],
        "stagnation_observed": diagnostics["stagnation_observed"],
        "best_position": result.best_position,
        "best_score": result.best_score,
        "best_so_far_position_history": trajectory["best_so_far_positions"],
        "best_so_far_history": trajectory["best_so_far"],
        "current_candidate_history": trajectory["path"],
        "candidate_score_history": trajectory["scores"],
        "candidate_path": trajectory["path"],
        "function_evaluations": result.function_evaluations,
        "iterations_completed": result.iterations_completed,
        "runtime_ms": result.runtime_ms,
        "effective_seed": result.effective_seed,
        "parameters": result.parameters,
        "termination_reason": result.termination_reason,
        "diagnostics": diagnostics,
        "error": result.error,
        "distance_to_nearest_global_minimum": diagnostics["nearest_global_minimum_distance"],
        "within_success_tolerance": diagnostics["target_attained"],
        "success_rate": stats["success_rate"],
        "target_attainment_rate": stats["target_attainment_rate"],
        "median_score": stats["median_score"],
        "score_spread": stats["score_spread"],
        "trial_results": trial_rows,
    }
    return row, trajectory


def build_report(*, experiment_id: str, created_at: str, request, problem, bounds: dict[str, tuple[float, float]], landscape: dict[str, Any], results: list, trial_results: dict[str, list], total_runtime_ms: float) -> dict[str, Any]:
    report_started = time.perf_counter()
    result_rows: list[dict[str, Any]] = []
    animation: dict[str, Any] = {"algorithms": {}}
    warnings: list[str] = []
    for result in results:
        row, trajectory = _result_row(result, problem, bounds, trial_results.get(result.algorithm, [result]))
        result_rows.append(row)
        animation["algorithms"][result.algorithm] = trajectory
        if row["execution_status"] == "failed":
            warnings.append(f"{result.display_name} failed: {result.error or result.termination_reason}")
        if row["stagnation_observed"]:
            warnings.append(f"{result.display_name} showed measured stagnation; the cause is not established by this experiment.")
    comparison_selection = select_winner(result_rows, request.comparison.ranking_metric)
    winner = comparison_selection["winner"]
    fastest = fastest_algorithm(result_rows)
    execution_succeeded_count = sum(bool(row["execution_succeeded"]) for row in result_rows)
    completed_count = sum(row["execution_status"] == "completed" for row in result_rows)
    early_stopped_count = sum(row["execution_status"] == "early_stopped" for row in result_rows)
    failed_count = sum(row["execution_status"] == "failed" for row in result_rows)
    total_evaluations = sum(row["function_evaluations"] for row in result_rows)
    target_algorithms = [row["algorithm"] for row in result_rows if row["target_attained"]]
    optimization_successes = [row["algorithm"] for row in result_rows if row["optimization_success"]]
    stagnated_algorithms = [row["algorithm"] for row in result_rows if row["stagnation_observed"]]
    failed_algorithms = [row["algorithm"] for row in result_rows if row["execution_status"] == "failed"]
    report = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "status": "completed" if execution_succeeded_count else "failed",
        "execution_status": "failed" if failed_count == len(result_rows) else ("partial" if failed_count else "completed"),
        "created_at": created_at,
        "config": {"function": problem.identifier, "algorithms": request.algorithms, "iterations": request.iterations, "seed": request.seed, "starting_point": list(request.starting_point) if request.starting_point is not None else None, "bounds": {"x": list(bounds["x"]), "y": list(bounds["y"])}, "parameters": {key: value for key, value in request.parameters.items()}, "landscape_resolution": request.landscape.resolution, "repeated_trials": request.repeated_trials, "include_population_snapshots": request.include_population_snapshots, "effective_seeds": {row["algorithm"]: row["effective_seed"] for row in result_rows}, "total_runtime_ms": total_runtime_ms},
        "problem": problem.metadata({"x": list(bounds["x"]), "y": list(bounds["y"])}),
        "landscape": landscape,
        "results": result_rows,
        "animation": animation,
        "convergence": {"series": [{"algorithm": row["algorithm"], "display_name": row["display_name"], "iterations": animation["algorithms"][row["algorithm"]]["iterations"], "function_evaluations": animation["algorithms"][row["algorithm"]]["function_evaluations"], "best_so_far": animation["algorithms"][row["algorithm"]]["best_so_far"]} for row in result_rows], "note": "Iteration/generation indices are algorithm-specific; function evaluations are the comparable computational axis."},
        "comparison": {"ranking_metric": request.comparison.ranking_metric, "winner": winner, "fastest_algorithm": fastest, "ranking": comparison_selection["ranking"], "ranking_method": comparison_selection["explanation"], "limitations": ["Runtime ranking is machine-dependent.", "A single trial does not establish statistical reliability."] if request.repeated_trials == 1 else ["Results remain dependent on the selected seed and finite budgets."]},
        "diagnostics": {"algorithm_count_requested": len(request.algorithms), "algorithm_count_completed": completed_count, "algorithm_count_early_stopped": early_stopped_count, "algorithm_count_execution_succeeded": execution_succeeded_count, "algorithm_count_failed": failed_count, "total_function_evaluations": total_evaluations, "numerical_validation": "passed", "warnings": warnings, "report_generation_duration_ms": (time.perf_counter() - report_started) * 1000},
        "overall_summary": {"lowest_valid_objective_algorithm": min((row["algorithm"] for row in result_rows if row["best_score"] is not None), key=lambda name: next(row["best_score"] for row in result_rows if row["algorithm"] == name), default=None), "fastest_successfully_completed_algorithm": fastest, "selected_algorithm": winner["algorithm"] if winner else None, "execution_completed_algorithms": [row["algorithm"] for row in result_rows if row["execution_status"] == "completed"], "optimization_successful_algorithms": optimization_successes, "target_attained_algorithms": target_algorithms, "stagnated_algorithms": stagnated_algorithms, "failed_algorithms": failed_algorithms, "global_optimum_reached_within_tolerance": bool(target_algorithms), "key_differences": "Solution quality, target attainment, stagnation, failures and runtime are reported separately; the ranking metric determines the recommendation.", "stalled_or_failed": bool(stagnated_algorithms or failed_algorithms), "limitations": ["Runtime ranking is machine-dependent.", "A single trial does not establish statistical reliability."] if request.repeated_trials == 1 else ["Results remain dependent on the selected seed and finite budgets."]},
        "ai_insights": None,
        "metadata": {"backend_version": __version__, "created_at_utc": datetime.now(timezone.utc).isoformat(), "data_omitted": ["population snapshots are omitted unless explicitly requested"]},
    }
    return validate_report(report)
