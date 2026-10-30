"""Health check endpoint verifying service and database connectivity."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """Return service health and database connection status."""
    db.execute(text("SELECT 1"))
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
        "database": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

