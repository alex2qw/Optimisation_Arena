from fastapi import APIRouter

from app.algorithms import get_algorithm_metadata

router = APIRouter(tags=["catalog"])


@router.get("/api/algorithms")
def algorithms() -> dict:
    return {"algorithms": get_algorithm_metadata()}
