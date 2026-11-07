from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas import ExperimentRequest
from app.services.experiment_runner import get_report, run_experiment

router = APIRouter(tags=["experiments"])


@router.post("/api/experiments", status_code=201)
def create_experiment(request: ExperimentRequest) -> dict:
    try:
        return run_experiment(request, get_settings())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "type": "invalid_experiment"}) from exc


@router.get("/api/experiments/{experiment_id}")
def retrieve_experiment(experiment_id: str) -> dict:
    report = get_report(experiment_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Experiment not found. Reports are in-memory and expire on process restart.")
    return report


@router.get("/api/experiments/{experiment_id}/summary")
def experiment_summary(experiment_id: str) -> dict:
    report = get_report(experiment_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return {"experiment_id": report["experiment_id"], "status": report["status"], "created_at": report["created_at"], "function": report["config"]["function"], "algorithms": report["config"]["algorithms"], "winner": report["comparison"]["winner"], "fastest_algorithm": report["comparison"]["fastest_algorithm"], "total_runtime_ms": report["config"]["total_runtime_ms"], "warnings": report["diagnostics"]["warnings"]}
