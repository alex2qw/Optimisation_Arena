from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import algorithms, experiments, functions, health, insights
from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version=__version__, docs_url="/docs", openapi_url="/api/openapi.json", description="Stateless numerical optimisation experiments for Optimisation Arena.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(health.router)
app.include_router(functions.router)
app.include_router(algorithms.router)
app.include_router(experiments.router)
app.include_router(insights.router)
