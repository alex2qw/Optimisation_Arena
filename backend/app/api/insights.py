from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas import InsightRequest
from app.services.ai_insights import generate_insights
from app.services.experiment_runner import get_insights, get_report, store_insights

router = APIRouter(tags=["insights"])


@router.post("/api/experiments/{experiment_id}/insights")
def create_insights(experiment_id: str, request: InsightRequest = InsightRequest()) -> dict:
    report = get_report(experiment_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    if not request.force_refresh:
        cached = get_insights(experiment_id)
        if cached is not None:
            return cached
    insights = generate_insights(report, get_settings())
    store_insights(experiment_id, insights)
    return insights


@router.get("/api/experiments/{experiment_id}/insights")
def retrieve_insights(experiment_id: str) -> dict:
    if get_report(experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    insights = get_insights(experiment_id)
    if insights is None:
        return {"status": "not_generated", "experiment_id": experiment_id, "message": "Insights have not been requested for this experiment."}
    return insights
