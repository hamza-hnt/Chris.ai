from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.domain.models import (
    AgentContext,
    Lease,
    Organization,
    Payment,
    Property,
    PropertyPreferredProvider,
    Provider,
    User,
    UserRole,
)


DEMO_TENANT_PHONE = "+33600000001"
DEMO_LANDLORD_PHONE = "+33600000002"


def seed() -> None:
    with SessionLocal() as db:
        org = db.execute(select(Organization).where(Organization.name == "Demo Agency")).scalar_one_or_none()
        if org is None:
            org = Organization(name="Demo Agency")
            db.add(org)
            db.flush()

        tenant = _user(
            db,
            org.id,
            role=UserRole.tenant,
            name="Amina Tenant",
            email="amina.tenant@example.com",
            phone=DEMO_TENANT_PHONE,
        )
        landlord = _user(
            db,
            org.id,
            role=UserRole.landlord,
            name="Marc Landlord",
            email="marc.landlord@example.com",
            phone=DEMO_LANDLORD_PHONE,
        )
        _user(
            db,
            org.id,
            role=UserRole.supervisor,
            name="Chris Supervisor",
            email="supervisor@example.com",
            phone="+33600000003",
        )

        prop = db.execute(
            select(Property).where(Property.address == "12 Rue de Rivoli, 75004 Paris")
        ).scalar_one_or_none()
        if prop is None:
            prop = Property(
                org_id=org.id,
                address="12 Rue de Rivoli, 75004 Paris",
                type="apartment",
                size="48 sqm",
                equipment={"heating": "electric", "water_heater": "individual"},
                access_details={"building_code": "1234A", "floor": "3"},
            )
            db.add(prop)
            db.flush()

        lease = db.execute(select(Lease).where(Lease.property_id == prop.id)).scalar_one_or_none()
        if lease is None:
            lease = Lease(
                property_id=prop.id,
                tenant_id=tenant.id,
                landlord_id=landlord.id,
                rent=Decimal("1250.00"),
                charges=Decimal("120.00"),
                payment_due_day=5,
                deposit=Decimal("1250.00"),
                start_date=date(2026, 1, 1),
                end_date=None,
                lease_type="primary residence",
            )
            db.add(lease)
            db.flush()

        if (
            db.execute(
                select(Payment).where(Payment.lease_id == lease.id, Payment.period == "2026-05")
            ).scalar_one_or_none()
            is None
        ):
            db.add(Payment(lease_id=lease.id, period="2026-05", amount=Decimal("1370.00")))

        provider = db.execute(
            select(Provider).where(Provider.org_id == org.id, Provider.name == "Paris Plomberie Service")
        ).scalar_one_or_none()
        if provider is None:
            provider = Provider(
                org_id=org.id,
                name="Paris Plomberie Service",
                trade="plumber",
                contacts={"email": "contact@paris-plomberie.invalid", "phone": "+33100000000"},
            )
            db.add(provider)
            db.flush()

        preferred = db.get(PropertyPreferredProvider, (prop.id, provider.id))
        if preferred is None:
            db.add(PropertyPreferredProvider(property_id=prop.id, provider_id=provider.id, rank=1))

        if db.get(AgentContext, prop.id) is None:
            db.add(
                AgentContext(
                    property_id=prop.id,
                    summary="Demo property for the Chris.AI bootstrap.",
                    sensitive_notes={"landlord_preferences": "Approve spend before provider dispatch."},
                )
            )

        db.commit()
        print(f"Seeded demo property: {prop.id}")
        print(f"Tenant phone: {DEMO_TENANT_PHONE}")
        print(f"Landlord phone: {DEMO_LANDLORD_PHONE}")


def _user(db, org_id, role: UserRole, name: str, email: str, phone: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(org_id=org_id, role=role, name=name, email=email, phone=phone)
        db.add(user)
        db.flush()
    return user


if __name__ == "__main__":
    seed()
