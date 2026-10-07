from datetime import datetime, timezone
from fastapi import APIRouter
import pyogrio

from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service health check")
def health_check():
    drivers = []
    try:
        available = pyogrio.list_drivers()
        for target in ["KML", "LIBKML", "ESRI Shapefile"]:
            if target in available:
                drivers.append(target)
    except Exception:
        pass

    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "supported_drivers": drivers,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
