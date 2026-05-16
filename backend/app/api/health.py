from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.db import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def health_db() -> dict[str, str]:
    try:
        check_database()
    except Exception as exc:  # pragma: no cover - exercised in running stack
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok"}


@router.get("/health/config")
def health_config() -> dict:
    return {"status": "ok", "settings": get_settings().safe_boot_summary()}
