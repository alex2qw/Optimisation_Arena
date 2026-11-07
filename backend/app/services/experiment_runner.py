import hashlib
import time
import uuid
from datetime import datetime, timezone
from threading import RLock
from typing import Any

import numpy as np

from app.algorithms import run_algorithm
from app.problems import get_problem
from app.schemas import ExperimentRequest, GeneticAlgorithmParameters, GradientDescentParameters, SimulatedAnnealingParameters

from .landscape_generator import generate_landscape
from .ai_insights import generate_insights
from .report_builder import build_report, validate_report

REPORT_STORE: dict[str, dict[str, Any]] = {}
INSIGHT_STORE: dict[str, dict[str, Any]] = {}
STORE_LOCK = RLock()
MAX_STORED_REPORTS = 100


def _effective_seed(seed: int, algorithm: str, trial: int) -> int:
    digest = hashlib.sha256(f"{seed}:{algorithm}:{trial}".encode()).digest()
    return int.from_bytes(digest[:4], "big", signed=False)


def _bounds_for_request(request: ExperimentRequest, problem) -> dict[str, tuple[float, float]]:
    if request.bounds is not None:
        return {"x": tuple(request.bounds.x), "y": tuple(request.bounds.y)}
    return {"x": problem.default_bounds, "y": problem.default_bounds}


def run_experiment(request: ExperimentRequest, settings) -> dict[str, Any]:
    problem = get_problem(request.function)
    supported = {"gradient_descent", "simulated_annealing", "genetic_algorithm"}
    unknown = [name for name in request.algorithms if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported algorithm(s): {', '.join(unknown)}")
    parameter_models = {"gradient_descent": GradientDescentParameters, "simulated_annealing": SimulatedAnnealingParameters, "genetic_algorithm": GeneticAlgorithmParameters}
    unexpected_parameter_sets = set(request.parameters) - set(request.algorithms)
    if unexpected_parameter_sets:
        raise ValueError(f"parameters supplied for unselected algorithm(s): {', '.join(sorted(unexpected_parameter_sets))}")
    for algorithm in request.algorithms:
        try:
            parameter_models[algorithm].model_validate(request.parameters.get(algorithm, {}))
        except Exception as exc:
            raise ValueError(f"invalid parameters for {algorithm}: {exc}") from exc
    bounds = _bounds_for_request(request, problem)
    if request.starting_point is not None:
        start = np.asarray(request.starting_point, dtype=float)
        if not (bounds["x"][0] <= start[0] <= bounds["x"][1] and bounds["y"][0] <= start[1] <= bounds["y"][1]):
            raise ValueError("starting_point must be inside the selected bounds")
    else:
        rng = np.random.default_rng(request.seed)
        start = np.array([rng.uniform(*bounds["x"]), rng.uniform(*bounds["y"])], dtype=float)
    if request.landscape.resolution > settings.max_landscape_resolution:
        raise ValueError(f"landscape resolution cannot exceed {settings.max_landscape_resolution}")
    if request.iterations > settings.max_iterations or request.iterations + 1 > settings.max_trajectory_points:
        raise ValueError(f"iterations cannot exceed the configured trajectory limit ({min(settings.max_iterations, settings.max_trajectory_points - 1)})")
    if request.repeated_trials > settings.max_repeated_trials:
        raise ValueError(f"repeated_trials cannot exceed {settings.max_repeated_trials}")
    max_evaluations = request.max_evaluations or settings.max_evaluations
    if max_evaluations > settings.max_evaluations:
        raise ValueError(f"max_evaluations cannot exceed {settings.max_evaluations}")
    landscape = generate_landscape(problem, bounds, request.landscape.resolution)
    started = time.perf_counter()
    selected_results = []
    trial_results: dict[str, list] = {}
    for algorithm in request.algorithms:
        runs = []
        for trial in range(request.repeated_trials):
            effective_seed = _effective_seed(request.seed, algorithm, trial)
            try:
                result = run_algorithm(algorithm, problem, ((bounds["x"][0], bounds["x"][1]), (bounds["y"][0], bounds["y"][1])), start, request.iterations, effective_seed, request.parameters.get(algorithm, {}), max_evaluations, request.include_population_snapshots)
            except Exception as exc:
                from app.algorithms.base import AlgorithmResult, ALGORITHM_NAMES
                result = AlgorithmResult(algorithm, ALGORITHM_NAMES[algorithm], "failed", None, None, effective_seed=effective_seed, parameters=request.parameters.get(algorithm, {}), termination_reason="configuration or execution error", error=str(exc))
            runs.append(result)
        best_run = min((item for item in runs if item.best_score is not None), key=lambda item: item.best_score, default=runs[0])
        selected_results.append(best_run)
        trial_results[algorithm] = runs
    experiment_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    report = build_report(experiment_id=experiment_id, created_at=created_at, request=request, problem=problem, bounds=bounds, landscape=landscape, results=selected_results, trial_results=trial_results, total_runtime_ms=(time.perf_counter() - started) * 1000)
    # AI is optional: without a key this returns a structured unavailable/disabled
    # result immediately; with a configured key it enriches this same report.
    ai_started = time.perf_counter()
    report["ai_insights"] = generate_insights(report, settings)
    report["metadata"]["ai_generation_duration_ms"] = (time.perf_counter() - ai_started) * 1000
    if report["ai_insights"].get("status") in {"failed", "unavailable", "disabled"}:
        report["diagnostics"]["warnings"].append(f"AI insights status: {report['ai_insights']['status']}.")
    report["config"]["total_runtime_ms"] = (time.perf_counter() - started) * 1000
    validate_report(report)
    with STORE_LOCK:
        REPORT_STORE[experiment_id] = report
        INSIGHT_STORE[experiment_id] = report["ai_insights"]
        while len(REPORT_STORE) > MAX_STORED_REPORTS:
            REPORT_STORE.pop(next(iter(REPORT_STORE)))
    return report


def get_report(experiment_id: str) -> dict[str, Any] | None:
    with STORE_LOCK:
        return REPORT_STORE.get(experiment_id)


def get_insights(experiment_id: str) -> dict[str, Any] | None:
    with STORE_LOCK:
        return INSIGHT_STORE.get(experiment_id)


def store_insights(experiment_id: str, insights: dict[str, Any]) -> None:
    with STORE_LOCK:
        INSIGHT_STORE[experiment_id] = insights
        if experiment_id in REPORT_STORE:
            REPORT_STORE[experiment_id]["ai_insights"] = insights
