import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_and_catalog_endpoints():
    assert client.get("/api/health").status_code == 200
    assert len(client.get("/api/functions").json()["functions"]) == 4
    assert len(client.get("/api/algorithms").json()["algorithms"]) == 3


def test_api_experiment_and_retrieval():
    response = client.post("/api/experiments", json={"function": "sphere", "algorithms": ["gradient_descent"], "iterations": 8, "landscape": {"resolution": 10}})
    assert response.status_code == 201, response.text
    report = response.json()
    assert report["experiment_id"]
    assert client.get(f"/api/experiments/{report['experiment_id']}").status_code == 200
    assert client.get(f"/api/experiments/{report['experiment_id']}/summary").status_code == 200
    json.dumps(report, allow_nan=False)


def test_invalid_requests_and_missing_report():
    assert client.post("/api/experiments", json={"function": "not-a-function", "algorithms": ["gradient_descent"]}).status_code == 422
    assert client.post("/api/experiments", json={"function": "sphere", "algorithms": ["gradient_descent"], "bounds": {"x": [1, 1], "y": [-1, 1]}}).status_code == 422
    assert client.get("/api/experiments/missing").status_code == 404
    assert client.get("/api/experiments/missing/insights").status_code == 404
    assert client.post("/api/experiments", json={"function": "sphere", "algorithms": ["gradient_descent"], "parameters": {"gradient_descent": {"learning_rate": -1}}}).status_code == 422
