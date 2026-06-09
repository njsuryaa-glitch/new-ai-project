from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Observability Health Check"
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Checks status of critical system components:
    - PostgreSQL connection
    - LLM service availability
    """
    # 1. Check Database connection
    db_status = "disconnected"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Health check database connection failure: {e}")
        
    # 2. Check LLM credentials/availability
    llm_status = "unavailable"
    if settings.GEMINI_API_KEY:
        # Check that we have a key configured. In a deeper check we could run a mock request,
        # but to keep health check fast and cheap, we check key existence.
        llm_status = "available"
    else:
        logger.warning("Health check: Gemini API Key is missing.")

    # 3. Determine overall status
    overall_status = "healthy" if db_status == "connected" and llm_status == "available" else "unhealthy"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        llm=llm_status
    )
