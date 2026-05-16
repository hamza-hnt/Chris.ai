from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.domain.models import ActionLog, Lease, PropertyPreferredProvider, Provider, User, UserRole


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
        return _resolve_provider(db, contact)

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


def _resolve_provider(db: Session, contact: str) -> RouteResult | None:
    provider = _find_provider_by_contact(db, contact)
    if provider is None:
        return None

    recent_contact = (
        db.execute(
            select(ActionLog)
            .where(ActionLog.kind == "provider.contact")
            .order_by(desc(ActionLog.created_at))
        )
        .scalars()
        .all()
    )
    for action in recent_contact:
        if str((action.payload or {}).get("provider_id")) == str(provider.id):
            return RouteResult(property_id=action.property_id, sender_role="provider")

    preferred = db.execute(
        select(PropertyPreferredProvider).where(PropertyPreferredProvider.provider_id == provider.id)
    ).scalars().first()
    if preferred:
        return RouteResult(property_id=preferred.property_id, sender_role="provider")
    return None


def _find_provider_by_contact(db: Session, contact: str) -> Provider | None:
    normalized = contact.strip().lower()
    phone = _normalize_phone(contact)
    providers = db.execute(select(Provider)).scalars().all()
    for provider in providers:
        contacts = provider.contacts or {}
        provider_phone = _normalize_phone(str(contacts.get("phone", "")))
        provider_email = str(contacts.get("email", "")).lower()
        if provider_phone and provider_phone == phone:
            return provider
        if provider_email and provider_email == normalized:
            return provider
    return None


def _normalize_phone(value: str) -> str:
    clean = value.strip().replace(" ", "").replace(".", "").replace("-", "")
    if clean.startswith("00"):
        clean = f"+{clean[2:]}"
    if clean.startswith("0") and len(clean) == 10:
        clean = f"+33{clean[1:]}"
    return clean
