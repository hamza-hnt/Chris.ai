from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Property, PropertyPreferredProvider, Provider
from app.domain.repositories.serialization import model_to_dict
from app.orchestration.isolation import scoped


def list_preferred_providers(property_id: UUID, db: Session, trade: str | None = None) -> list[dict]:
    with scoped(property_id) as pid:
        statement = (
            select(PropertyPreferredProvider)
            .where(PropertyPreferredProvider.property_id == pid)
            .order_by(PropertyPreferredProvider.rank.asc())
        )
        rows = db.execute(statement).scalars()
        result = []
        for row in rows:
            provider = row.provider
            if trade and provider.trade.lower() != trade.lower():
                continue
            result.append(
                {
                    "rank": row.rank,
                    "provider": model_to_dict(provider, ["id", "name", "trade", "contacts"]),
                }
            )
        return result


def get_provider(property_id: UUID, db: Session, provider_id: UUID) -> Provider:
    with scoped(property_id) as pid:
        prop = db.get(Property, pid)
        provider = db.execute(
            select(Provider).where(Provider.id == provider_id, Provider.org_id == prop.org_id)
        ).scalar_one()
        return provider
