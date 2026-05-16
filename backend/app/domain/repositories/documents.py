from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Document, DocumentKind, Lease, Payment
from app.domain.repositories.serialization import model_to_dict
from app.orchestration.isolation import scoped


class DocumentRefusal(ValueError):
    pass


def create_receipt(property_id: UUID, db: Session, payment_id: UUID, triggered_by: str) -> Document:
    with scoped(property_id) as pid:
        payment = db.execute(
            select(Payment)
            .join(Lease, Payment.lease_id == Lease.id)
            .where(Payment.id == payment_id, Lease.property_id == pid)
        ).scalar_one_or_none()
        if payment is None:
            raise DocumentRefusal("Payment does not belong to this property.")
        if payment.confirmed_by_landlord_at is None:
            raise DocumentRefusal("Receipt refused: payment is not confirmed by the landlord.")

        lease = payment.lease
        tenant = lease.tenant
        landlord = lease.landlord
        payload = {
            "source": "relational",
            "kind": "receipt",
            "payment": model_to_dict(
                payment,
                ["id", "period", "amount", "confirmed_by_landlord_at"],
            ),
            "lease": model_to_dict(
                lease,
                ["id", "rent", "charges", "payment_due_day", "deposit", "start_date", "end_date"],
            ),
            "tenant": model_to_dict(tenant, ["id", "name", "email", "phone"]),
            "landlord": model_to_dict(landlord, ["id", "name", "email", "phone"]),
        }
        document = Document(
            property_id=pid,
            kind=DocumentKind.receipt,
            payload=payload,
            triggered_by=triggered_by,
        )
        db.add(document)
        db.flush()
        payment.receipt_document_id = document.id
        db.flush()
        return document


def create_stub_document(
    property_id: UUID,
    db: Session,
    kind: DocumentKind,
    payload: dict,
    triggered_by: str,
) -> Document:
    with scoped(property_id) as pid:
        document = Document(
            property_id=pid,
            kind=kind,
            payload={"source": "relational_stub", **payload},
            triggered_by=triggered_by,
        )
        db.add(document)
        db.flush()
        return document
