from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.supervisor.dashboard import build_landlord_dashboard, build_tenant_dashboard
from app.db import get_db
from app.domain.models import User, UserRole

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/dashboard")
def portal_dashboard(
    x_user_id: UUID | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> dict:
    user = _current_user(db, x_user_id)
    if user.role == UserRole.landlord:
        return build_landlord_dashboard(db, user)
    if user.role == UserRole.tenant:
        return build_tenant_dashboard(db, user)
    raise HTTPException(status_code=403, detail="Portal dashboard is for landlords and tenants.")


def _current_user(db: Session, user_id: UUID | None) -> User:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header.")
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid user session.")
    return user
