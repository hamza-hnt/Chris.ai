from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.models import Lease, User, UserRole


SenderRole = Literal["tenant", "landlord", "provider", "supervisor"]


@dataclass(frozen=True)
class RouteResult:
    property_id: UUID
    sender_role: SenderRole
    user_id: UUID | None = None


def resolve_sender(db: Session, sender_contact: str) -> RouteResult | None:
    contact = sender_contact.strip()
    if not contact:
        return None

    user = db.execute(
        select(User).where(or_(User.phone == contact, User.email == contact))
    ).scalar_one_or_none()
    if user is None:
        return None

    if user.role == UserRole.tenant:
        lease = db.execute(select(Lease).where(Lease.tenant_id == user.id)).scalar_one_or_none()
        if lease:
            return RouteResult(property_id=lease.property_id, sender_role="tenant", user_id=user.id)
    if user.role == UserRole.landlord:
        lease = db.execute(select(Lease).where(Lease.landlord_id == user.id)).scalar_one_or_none()
        if lease:
            return RouteResult(property_id=lease.property_id, sender_role="landlord", user_id=user.id)
    if user.role == UserRole.supervisor:
        lease = db.execute(select(Lease)).scalars().first()
        if lease:
            return RouteResult(property_id=lease.property_id, sender_role="supervisor", user_id=user.id)

    return None
