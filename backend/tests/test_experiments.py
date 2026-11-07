import json

from app.config import get_settings
from app.schemas import ExperimentRequest
from app.services.experiment_runner import run_experiment


def test_report_contains_surface_animation_and_comparison(offline_settings):
    request = ExperimentRequest(function="rastrigin", algorithms=["gradient_descent", "simulated_annealing"], iterations=12, seed=42, starting_point=(3.5, -2.5), landscape={"resolution": 12})
    report = run_experiment(request, offline_settings)
    assert report["ai_insights"] is not None
    assert report["ai_insights"]["status"] in {"disabled", "unavailable", "completed", "failed"}
    assert report["landscape"]["surface"]["resolution"] == 12
    assert len(report["landscape"]["surface"]["z"]) == 12
    assert len(report["landscape"]["surface"]["z"][0]) == 12
    surface = report["landscape"]["surface"]
    assert surface["z"][4][7] == problem_value("rastrigin", surface["x"][7], surface["y"][4])
    for algorithm in request.algorithms:
        animation = report["animation"]["algorithms"][algorithm]
        assert len(animation["path"]) == len(animation["scores"]) == len(animation["best_so_far"]) == len(animation["iterations"])
        assert all(animation["best_so_far"][i] <= animation["best_so_far"][i - 1] + 1e-10 for i in range(1, len(animation["best_so_far"])))
    json.dumps(report, allow_nan=False)


def problem_value(identifier, x, y):
    from app.problems import get_problem

    return get_problem(identifier).objective((x, y))


def test_invalid_start_is_rejected(offline_settings):
    request = ExperimentRequest(function="sphere", algorithms=["gradient_descent"], starting_point=(100, 100))
    try:
        run_experiment(request, offline_settings)
    except ValueError as exc:
        assert "starting_point" in str(exc)
    else:
        raise AssertionError("invalid start was accepted")
