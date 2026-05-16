from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.domain.models import (
    ActionLog,
    AgentContext,
    Conversation,
    ConversationParty,
    Lease,
    Organization,
    Payment,
    Plan,
    PlanStatus,
    Property,
    PropertyPreferredProvider,
    Provider,
    User,
    UserRole,
)


DEMO_TENANT_PHONE = "+33600000001"
DEMO_TENANT_2_PHONE = "+33600000004"
DEMO_LANDLORD_PHONE = "+33783913305"


def seed() -> None:
    with SessionLocal() as db:
        existing_org = db.execute(select(Organization).where(Organization.name == "Demo Agency")).scalar_one_or_none()
        if existing_org is not None:
            db.execute(delete(Property).where(Property.org_id == existing_org.id))
            db.execute(delete(Provider).where(Provider.org_id == existing_org.id))
            db.execute(delete(User).where(User.org_id == existing_org.id))
            db.execute(delete(Organization).where(Organization.id == existing_org.id))
            db.flush()

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
        tenant_2 = _user(
            db,
            org.id,
            role=UserRole.tenant,
            name="Hugo Tenant",
            email="hugo.tenant@example.com",
            phone=DEMO_TENANT_2_PHONE,
        )
        landlord = _user(
            db,
            org.id,
            role=UserRole.landlord,
            name="Hamza",
            email="hamza.landlord@example.com",
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

        first = _seed_unit(
            db,
            org_id=org.id,
            landlord=landlord,
            tenant=tenant,
            provider=provider,
            address="12 Rue de Rivoli, 75004 Paris",
            property_type="apartment",
            size="48 sqm",
            equipment={"heating": "electric", "water_heater": "individual"},
            access_details={"building_code": "1234A", "floor": "3"},
            rent=Decimal("1250.00"),
            charges=Decimal("120.00"),
            deposit=Decimal("1250.00"),
            payment_due_day=5,
            payment_period="2026-05",
            plan_name="Request: Kitchen sink leak and plumber approval",
            plan_steps=[
                {
                    "description": "Review tenant report and confirm this is a plumbing request.",
                    "status": "done",
                    "evidence": "Tenant reported a leak under the kitchen sink.",
                },
                {
                    "description": "Ask landlord which approved provider Chris should contact.",
                    "status": "pending",
                },
                {
                    "description": "Coordinate provider visit and update tenant.",
                    "status": "pending",
                },
            ],
            context_summary="Amina has an active plumbing request. Landlord approval is needed before provider dispatch.",
        )
        second = _seed_unit(
            db,
            org_id=org.id,
            landlord=landlord,
            tenant=tenant_2,
            provider=provider,
            address="44 Avenue Ledru-Rollin, 75012 Paris",
            property_type="studio",
            size="31 sqm",
            equipment={"heating": "central", "appliances": ["fridge", "washer"]},
            access_details={"building_code": "7788B", "floor": "5"},
            rent=Decimal("980.00"),
            charges=Decimal("95.00"),
            deposit=Decimal("980.00"),
            payment_due_day=3,
            payment_period="2026-05",
            plan_name="Request: Heating noise follow-up",
            plan_steps=[
                {
                    "description": "Acknowledge tenant report and classify urgency.",
                    "status": "done",
                    "evidence": "Tenant reported recurring heating noise at night.",
                },
                {
                    "description": "Collect one availability slot from the tenant.",
                    "status": "done",
                    "evidence": "Tenant is available Thursday morning.",
                },
                {
                    "description": "Contact preferred provider with a scoped brief.",
                    "status": "pending",
                },
            ],
            context_summary="Hugo has a heating-noise follow-up request. Tenant availability is already known.",
        )

        db.commit()
        print(f"Seeded demo properties: {first.id}, {second.id}")
        print(f"Tenant phone: {DEMO_TENANT_PHONE}")
        print(f"Tenant 2 phone: {DEMO_TENANT_2_PHONE}")
        print(f"Landlord phone: {DEMO_LANDLORD_PHONE}")


def _user(db, org_id, role: UserRole, name: str, email: str, phone: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(org_id=org_id, role=role, name=name, email=email, phone=phone)
        db.add(user)
        db.flush()
    return user


def _seed_unit(
    db,
    org_id,
    landlord: User,
    tenant: User,
    provider: Provider,
    address: str,
    property_type: str,
    size: str,
    equipment: dict,
    access_details: dict,
    rent: Decimal,
    charges: Decimal,
    deposit: Decimal,
    payment_due_day: int,
    payment_period: str,
    plan_name: str,
    plan_steps: list[dict],
    context_summary: str,
) -> Property:
    prop = db.execute(select(Property).where(Property.address == address)).scalar_one_or_none()
    if prop is None:
        prop = Property(
            org_id=org_id,
            address=address,
            type=property_type,
            size=size,
            equipment=equipment,
            access_details=access_details,
        )
        db.add(prop)
        db.flush()

    lease = db.execute(select(Lease).where(Lease.property_id == prop.id)).scalar_one_or_none()
    if lease is None:
        lease = Lease(
            property_id=prop.id,
            tenant_id=tenant.id,
            landlord_id=landlord.id,
            rent=rent,
            charges=charges,
            payment_due_day=payment_due_day,
            deposit=deposit,
            start_date=date(2026, 1, 1),
            end_date=None,
            lease_type="primary residence",
        )
        db.add(lease)
        db.flush()

    if (
        db.execute(
            select(Payment).where(Payment.lease_id == lease.id, Payment.period == payment_period)
        ).scalar_one_or_none()
        is None
    ):
        db.add(Payment(lease_id=lease.id, period=payment_period, amount=rent + charges))

    if db.get(PropertyPreferredProvider, (prop.id, provider.id)) is None:
        db.add(PropertyPreferredProvider(property_id=prop.id, provider_id=provider.id, rank=1))

    if db.get(AgentContext, prop.id) is None:
        db.add(
            AgentContext(
                property_id=prop.id,
                summary=context_summary,
                sensitive_notes={"landlord_preferences": "Approve spend before provider dispatch."},
            )
        )

    plan = db.execute(
        select(Plan).where(Plan.property_id == prop.id, Plan.name == plan_name)
    ).scalar_one_or_none()
    if plan is None:
        db.add(
            Plan(
                property_id=prop.id,
                name=plan_name,
                status=PlanStatus.active,
                steps=plan_steps,
            )
        )

    if (
        db.execute(
            select(Conversation).where(
                Conversation.property_id == prop.id,
                Conversation.party == ConversationParty.tenant,
                Conversation.thread_id == "seed-demo",
            )
        ).scalar_one_or_none()
        is None
    ):
        db.add(
            Conversation(
                property_id=prop.id,
                party=ConversationParty.tenant,
                thread_id="seed-demo",
                messages=[
                    {
                        "role": "tenant",
                        "body": plan_name.replace("Request: ", ""),
                        "ts": datetime.now(UTC).isoformat(),
                        "channel": "whatsapp",
                    }
                ],
            )
        )

    if (
        db.execute(
            select(ActionLog).where(
                ActionLog.property_id == prop.id,
                ActionLog.kind == "seed.request_created",
            )
        ).scalar_one_or_none()
        is None
    ):
        db.add(
            ActionLog(
                property_id=prop.id,
                kind="seed.request_created",
                payload={"plan_name": plan_name, "tenant_id": str(tenant.id)},
            )
        )

    return prop


if __name__ == "__main__":
    seed()
