from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.models import User, UserRole
from app.domain.repositories.serialization import model_to_dict

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginPayload(BaseModel):
    identifier: str


@router.get("/demo-users")
def demo_users(db: Session = Depends(get_db)) -> dict:
    users = (
        db.execute(
            select(User)
            .where(User.role.in_([UserRole.landlord, UserRole.tenant]))
            .order_by(User.role.asc(), User.name.asc())
        )
        .scalars()
        .all()
    )
    return {
        "users": [
            {
                **model_to_dict(user, ["id", "name", "email", "phone", "role"]),
                "identifier": user.email or user.phone,
            }
            for user in users
        ]
    }


@router.post("/login")
def login(payload: LoginPayload, db: Session = Depends(get_db)) -> dict:
    identifier = payload.identifier.strip()
    filters = [User.email == identifier, User.phone == identifier]
    if user_id := _uuid_or_none(identifier):
        filters.append(User.id == user_id)
    user = db.execute(select(User).where(or_(*filters))).scalar_one_or_none()
    if user is None or user.role not in {UserRole.landlord, UserRole.tenant}:
        raise HTTPException(status_code=401, detail="Unknown landlord or tenant account.")
    return {
        "token_type": "demo-user-id",
        "access_token": str(user.id),
        "user": model_to_dict(user, ["id", "name", "email", "phone", "role"]),
    }


def _uuid_or_none(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None
