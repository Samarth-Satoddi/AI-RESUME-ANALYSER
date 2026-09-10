import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger
from app.api.v1.api import api_router


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-grade backend for AI Resume Analyzer & Job Opportunity Matcher",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Startup event to ensure database tables exist
    @app.on_event("startup")
    async def on_startup():
        try:
            from app.db.base import Base
            from app.db.session import engine
            import app.db.models  # noqa: F401
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized successfully.")
        except Exception as e:
            logger.error(f"Database initialization warning: {e}")

    # Global custom exception handler
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(f"AppException on {request.method} {request.url.path}: {exc.code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "code": exc.code,
                "message": exc.detail,
                "extra": exc.extra,
            },
        )

    # Unhandled internal error handler
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled server exception on {request.method} {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred." if not settings.DEBUG else str(exc),
            },
        )

    # Observability Endpoints
    @app.get("/health", tags=["Observability"])
    async def health_check():
        """Liveness check endpoint."""
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "service": settings.APP_NAME,
            "version": "1.0.0",
        }

    @app.get("/ready", tags=["Observability"])
    async def readiness_check():
        """Readiness check endpoint verifying internal subsystems."""
        checks = {}
        # Check storage write capability
        try:
            test_file = os.path.join(settings.UPLOAD_DIR, ".ready_check")
            with open(test_file, "w") as f:
                f.write("ok")
            if os.path.exists(test_file):
                os.remove(test_file)
            checks["storage"] = "ready"
        except Exception as e:
            checks["storage"] = f"unready: {str(e)}"

        all_ready = all(v == "ready" for v in checks.values())
        return JSONResponse(
            status_code=status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "ready" if all_ready else "not_ready",
                "subsystems": checks,
            },
        )

    @app.get("/api/v1", tags=["Root"])
    async def api_v1_root():
        """API v1 base info endpoint."""
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "status": "operational",
            "ai_provider": settings.AI_PROVIDER,
            "docs": "/docs" if settings.DEBUG else "disabled",
        }

    # Mount API v1 Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_application()
