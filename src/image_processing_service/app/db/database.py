from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base

from ..core.config import get_settings

# Create declarative base for models
Base = declarative_base()

# Global variables for database connections
_async_engine = None
_async_session_factory = None


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        settings = get_settings()
        database_url = settings.absolute_database_url

        # Convert sync SQLite URL to async if needed
        if database_url.startswith("sqlite:///"):
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

        _async_engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
        )

    return _async_engine


def get_async_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        async_engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    async_session_factory = get_async_session_factory()
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    try:
        async_engine = get_async_engine()

        logger.info("Creating database tables...")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


async def drop_tables():
    try:
        async_engine = get_async_engine()

        logger.warning("Dropping all database tables...")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")

    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


# Dependency for FastAPI route injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_db_session():
        yield session


# Health check function
async def check_database_health() -> bool:
    try:
        async_engine = get_async_engine()
        async with async_engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
