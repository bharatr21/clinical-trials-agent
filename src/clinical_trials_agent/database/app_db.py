"""Application database for conversation metadata using SQLAlchemy async."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from clinical_trials_agent.config import get_settings
from clinical_trials_agent.models.conversation import Base

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


async def init_app_database() -> None:
    """Initialize the application database engine and create tables."""
    global _engine, _session_factory

    settings = get_settings()
    _engine = create_async_engine(
        settings.app_database_url_async,
        echo=False,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Application database initialized")


async def close_app_database() -> None:
    """Close the application database engine."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Application database closed")


@asynccontextmanager
async def get_app_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    Usage:
        async with get_app_db_session() as session:
            result = await session.execute(...)
    """
    if _session_factory is None:
        raise RuntimeError(
            "Application database not initialized. Call init_app_database() first."
        )

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
