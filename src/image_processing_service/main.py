from contextlib import asynccontextmanager
from pathlib import Path

from app.api import internal, public
from app.core.config import get_settings
from app.db.database import close_db, init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Image Processing Service...")

    database_dir = Path(settings.absolute_database_url.replace("sqlite:///", "")).parent
    storage_dirs = [
        settings.absolute_original_images_dir,
        settings.absolute_modified_images_dir,
        settings.absolute_temp_dir,
        str(database_dir),
    ]
    for dir_path in storage_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    logger.info("Storage directories initialized")

    await init_db()
    logger.info("Database initialized")
    logger.info("Image Processing Service startup complete")

    yield

    logger.info("Shutting down Image Processing Service...")
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Image Processing Service",
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

    # Mount static files for serving images
    if Path(settings.absolute_original_images_dir).exists():
        app.mount(
            "/static/original",
            StaticFiles(directory=settings.absolute_original_images_dir),
            name="original_images",
        )
    if Path(settings.absolute_modified_images_dir).exists():
        app.mount(
            "/static/modified",
            StaticFiles(directory=settings.absolute_modified_images_dir),
            name="modified_images",
        )

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
