from fastapi import APIRouter

from app.api.v1.endpoints import files, measurements, health

api_router = APIRouter()
api_router.include_router(files.router)
api_router.include_router(measurements.router)
api_router.include_router(health.router)
