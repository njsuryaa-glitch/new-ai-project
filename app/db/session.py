from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Connection pooling configurations to scale for high concurrent request volumes
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,          # Standard pool size of active connections
    max_overflow=30,      # Overflow connections allowed under load
    pool_timeout=30,       # Timeout for acquiring a connection from the pool
    pool_recycle=1800,     # Recycle connections older than 30 mins to avoid leaks
    pool_pre_ping=True     # Pre-ping database to drop dead connections automatically
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency yielding request-scoped async database sessions.
    Automatically handles session commit/rollback and cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
