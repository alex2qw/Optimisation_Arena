import json

import numpy as np
import pytest

from app.problems import get_problem
from app.schemas import ExperimentRequest
from app.services.experiment_runner import run_experiment
from app.services.report_builder import validate_report
from app.services.diagnostics import diagnose_result


PARAMETERS = {
    "gradient_descent": {"learning_rate": 0.001},
    "simulated_annealing": {"initial_temperature": 10, "cooling_rate": 0.95, "proposal_scale": 0.5},
    "genetic_algorithm": {"population_size": 10, "mutation_rate": 0.1, "mutation_strength": 0.2, "elite_count": 2},
}


@pytest.mark.parametrize("function", ["sphere", "rosenbrock", "rastrigin", "himmelblau"])
def test_full_report_is_frontend_ready_for_every_function(function, offline_settings):
    request = ExperimentRequest(function=function, algorithms=list(PARAMETERS), iterations=8, seed=2026, parameters=PARAMETERS, landscape={"resolution": 11}, max_evaluations=1000)
    report = run_experiment(request, offline_settings)
    validate_report(report)
    json.dumps(report, allow_nan=False)
    problem = get_problem(function)
    surface = report["landscape"]["surface"]
    for y_index in (0, 5, 10):
        for x_index in (0, 4, 10):
            assert surface["z"][y_index][x_index] == pytest.approx(problem.objective((surface["x"][x_index], surface["y"][y_index])))
    for algorithm in request.algorithms:
        animation = report["animation"]["algorithms"][algorithm]
        assert len(animation["path"]) == len(animation["scores"]) == len(animation["best_so_far"]) == len(animation["best_so_far_positions"]) == len(animation["iterations"]) == len(animation["function_evaluations"])
        assert animation["iterations"][0] == 0
        assert all(animation["best_so_far"][i] <= animation["best_so_far"][i - 1] + 1e-10 for i in range(1, len(animation["best_so_far"])))
        assert all(np.isfinite(value) for value in animation["scores"] + animation["best_so_far"])
    for series in report["convergence"]["series"]:
        animation = report["animation"]["algorithms"][series["algorithm"]]
        assert series["iterations"] == animation["iterations"]
        assert series["function_evaluations"] == animation["function_evaluations"]
        assert series["best_so_far"] == animation["best_so_far"]
    assert report["ai_insights"]["status"] == "disabled"
    assert report["overall_summary"]["target_attained_algorithms"] == [row["algorithm"] for row in report["results"] if row["target_attained"]]
    if report["comparison"]["winner"]:
        winner_algorithm = report["comparison"]["winner"]["algorithm"]
        assert winner_algorithm in request.algorithms
        assert any(row["algorithm"] == winner_algorithm and row["execution_succeeded"] for row in report["results"])
        valid_scores = [row["best_score"] for row in report["results"] if row["execution_succeeded"] and row["best_score"] is not None]
        assert report["comparison"]["winner"]["best_score"] == pytest.approx(min(valid_scores))


def test_failed_results_remain_strict_json_and_do_not_claim_success(monkeypatch, offline_settings):
    from app.algorithms.base import ALGORITHM_NAMES, AlgorithmResult
    import app.services.experiment_runner as runner

    def fail_algorithm(name, *args, **kwargs):
        return AlgorithmResult(name, ALGORITHM_NAMES[name], "failed", None, None, effective_seed=99, termination_reason="numerical failure", error="test failure")

    monkeypatch.setattr(runner, "run_algorithm", fail_algorithm)
    request = ExperimentRequest(function="sphere", algorithms=["gradient_descent"], iterations=4, landscape={"resolution": 10})
    report = run_experiment(request, offline_settings)
    json.dumps(report, allow_nan=False)
    row = report["results"][0]
    assert report["status"] == "failed"
    assert report["execution_status"] == "failed"
    assert row["execution_succeeded"] is False
    assert row["distance_to_nearest_global_minimum"] is None
    assert report["overall_summary"]["failed_algorithms"] == ["gradient_descent"]
    assert report["comparison"]["winner"] is None


def test_failed_execution_cannot_be_labelled_optimisation_success():
    diagnostics = diagnose_result({"scores": [10.0, 5.0], "best_so_far": [10.0, 5.0], "best_position": [1.0, 1.0], "best_score": 5.0, "status": "failed", "termination_reason": "numerical failure"}, [(0.0, 0.0)])
    assert diagnostics["execution_succeeded"] is False
    assert diagnostics["optimization_success"] is False
    assert diagnostics["optimization_status"] == "failed"


@pytest.mark.parametrize("function", ["sphere", "rosenbrock", "rastrigin", "himmelblau"])
@pytest.mark.parametrize("algorithm", ["gradient_descent", "simulated_annealing", "genetic_algorithm"])
def test_fixed_seed_reproduces_each_algorithm_on_each_problem(function, algorithm, offline_settings):
    request_kwargs = {"function": function, "algorithms": [algorithm], "iterations": 5, "seed": 31415, "landscape": {"resolution": 10}, "max_evaluations": 500}
    if algorithm == "gradient_descent":
        request_kwargs["parameters"] = {algorithm: {"learning_rate": 0.001}}
    elif algorithm == "simulated_annealing":
        request_kwargs["parameters"] = {algorithm: {"initial_temperature": 10, "cooling_rate": 0.95, "proposal_scale": 0.5}}
    else:
        request_kwargs["parameters"] = {algorithm: {"population_size": 8, "mutation_rate": 0.1, "mutation_strength": 0.2, "elite_count": 2}}
    first = run_experiment(ExperimentRequest(**request_kwargs), offline_settings)
    second = run_experiment(ExperimentRequest(**request_kwargs), offline_settings)
    first_row, second_row = first["results"][0], second["results"][0]
    assert first_row["best_score"] == second_row["best_score"]
    assert first["animation"]["algorithms"][algorithm]["path"] == second["animation"]["algorithms"][algorithm]["path"]
