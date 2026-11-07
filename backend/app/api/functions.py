from fastapi import APIRouter

from app.problems import list_problems

router = APIRouter(tags=["catalog"])


@router.get("/api/functions")
def functions() -> dict:
    return {"functions": [problem.metadata() for problem in list_problems()]}
