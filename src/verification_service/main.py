from contextlib import asynccontextmanager
from pathlib import Path

from app.api import internal, public
from app.core.config import get_settings
from app.db.database import close_db, init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Verification Service...")

    database_dir = Path(settings.absolute_database_url.replace("sqlite:///", "")).parent
    storage_dirs = [
        settings.absolute_temp_dir,
        settings.absolute_logs_dir,
        str(database_dir),
    ]
    for dir_path in storage_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    logger.info("Storage directories initialized")

    await init_db()
    logger.info("Database initialized")

    logger.info("Verification Service startup complete")

    yield

    logger.info("Shutting down Verification Service...")

    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Verification Service",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(public.router, prefix="/api", tags=["public"])
    app.include_router(internal.router, prefix="/internal", tags=["internal"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "verification"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
