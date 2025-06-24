from loguru import logger
from tortoise import Tortoise

from ..core.config import get_settings


async def init_db():
    try:
        settings = get_settings()
        database_url = settings.absolute_database_url

        # Convert sync SQLite URL to async if needed
        if database_url.startswith("sqlite:///"):
            database_url = database_url.replace("sqlite:///", "sqlite://")

        await Tortoise.init(
            db_url=database_url,
            modules={"models": []},
        )

        # Generate database schema
        await Tortoise.generate_schemas()

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def close_db():
    try:
        await Tortoise.close_connections()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
        raise


async def check_database_health() -> bool:
    try:
        from tortoise import connections

        # Get default connection and execute a simple query
        conn = connections.get("default")
        await conn.execute_query("SELECT 1")

        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
