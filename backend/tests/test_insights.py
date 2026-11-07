from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_insights import AIModelOutput, SuggestedParameters, generate_insights
from app.schemas import ExperimentRequest
from app.services.experiment_runner import run_experiment
from app.config import get_settings

client = TestClient(app)


def test_ai_unavailable_does_not_break_report():
    report = client.post("/api/experiments", json={"function": "sphere", "algorithms": ["gradient_descent"], "iterations": 2, "landscape": {"resolution": 10}}).json()
    response = client.post(f"/api/experiments/{report['experiment_id']}/insights", json={})
    assert response.status_code == 200
    assert response.json()["status"] in {"disabled", "unavailable", "completed", "failed"}
    refreshed_report = client.get(f"/api/experiments/{report['experiment_id']}").json()
    assert refreshed_report["ai_insights"]["status"] == response.json()["status"]


def test_ai_context_and_structured_response_are_validated(monkeypatch, offline_settings):
    captured = {}

    class FakeResponse:
        output_parsed = AIModelOutput(
            experiment_id="placeholder",
            headline="Measured summary",
            overall_analysis="The analysis uses the supplied measured report.",
            algorithm_insights=[{"algorithm": "gradient_descent", "observations": ["Improved"], "possible_explanations": ["Measured descent"], "confidence": "high"}],
            recommendations=[{"title": "Repeat the trial", "reason": "One run is limited", "expected_benefit": "More evidence", "suggested_parameters": SuggestedParameters(learning_rate=None, initial_temperature=None, cooling_rate=None, proposal_scale=None, population_size=None, mutation_rate=None, mutation_strength=None, elite_count=None)}],
            follow_up_experiments=["Repeat with another seed"],
            limitations=["Finite budget"],
        )

    class FakeResponses:
        def parse(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: FakeClient())
    report = run_experiment(ExperimentRequest(function="sphere", algorithms=["gradient_descent"], iterations=3, landscape={"resolution": 10}), offline_settings)
    ai_settings = get_settings().model_copy(update={"openai_api_key": "test-key", "openai_insights_enabled": True, "openai_model": "test-model"})
    insights = generate_insights(report, ai_settings)
    assert insights["status"] == "completed"
    assert insights["experiment_id"] == report["experiment_id"]
    assert captured["text_format"].__name__ == "AIModelOutput"
    assert report["experiment_id"] in captured["input"][1]["content"]
    assert report["comparison"]["winner"] is not None
