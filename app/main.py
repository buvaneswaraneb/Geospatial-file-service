from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_router
from app.config import settings
from app.core.handlers import register_exception_handlers
from app.core.logging import logger
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing %s v%s...", settings.PROJECT_NAME, settings.VERSION)
    settings.ensure_directories()
    init_db()
    logger.info("Database initialized successfully.")
    yield
    # Shutdown
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "Production-ready backend API that accepts geospatial files (Shapefile .zip or .kml), "
            "transforms geographic coordinates to optimal projected CRS (UTM/LAEA), and calculates "
            "accurate metric measurements (Area, Length)."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register custom exception handlers
    register_exception_handlers(application)

    # Mount API routes
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)
    application.include_router(health_router)

    @application.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    return application


app = create_application()
