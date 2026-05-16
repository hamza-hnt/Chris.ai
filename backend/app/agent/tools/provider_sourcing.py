import re
from uuid import UUID

from sqlalchemy import select

from app.agent.tools.executor import ToolExecutionContext
from app.domain.models import ActionLog, ConversationParty, Property, Provider
from app.domain.repositories.memory import append_action, append_message
from app.domain.repositories.providers import get_provider, list_preferred_providers
from app.domain.repositories.serialization import model_to_dict, to_jsonable
from app.integrations.email_stub import send_email
from app.integrations.tavily import tavily_search
from app.integrations.whatsapp_stub import send_whatsapp


def list_preferred(context: ToolExecutionContext, arguments: dict) -> dict:
    providers = list_preferred_providers(context.property_id, context.db, arguments.get("trade"))
    return {"ok": True, "providers": providers}


def search(context: ToolExecutionContext, arguments: dict) -> dict:
    trade = arguments["trade"].strip()
    property_address = _property_address(context)
    area = (arguments.get("area") or property_address).strip()
    constraints = (arguments.get("constraints") or "").strip()
    query = _provider_query(trade, area, property_address, constraints)
    result = tavily_search(query)
    candidates = _normalize_tavily_results(context, trade, result)
    append_action(
        context.property_id,
        context.db,
        "provider.search",
        {
            "trade": trade,
            "area": area,
            "property_address": property_address,
            "constraints": constraints,
            "query": query,
            "candidate_count": len(candidates),
        },
    )
    return {
        "ok": True,
        "trade": trade,
        "area": area,
        "property_address": property_address,
        "query": query,
        "candidates": candidates,
        "raw_search": to_jsonable(result),
    }


def register_contact(context: ToolExecutionContext, arguments: dict) -> dict:
    if context.sender_role not in {"landlord", "supervisor"}:
        return {
            "ok": False,
            "refused": True,
            "error": "Only the landlord or supervisor can supply an ad hoc repair provider.",
        }

    prop = _property(context)
    if prop is None:
        return {"ok": False, "error": "Property not found.", "refused": True}

    trade = (arguments.get("trade") or "general maintenance").strip()
    phone = _normalize_phone(arguments.get("phone"))
    email = (arguments.get("email") or "").strip().lower()
    if not phone and not email:
        return {"ok": False, "error": "A phone or email contact is required.", "refused": True}

    provider = _find_provider_by_contact(context, prop.org_id, phone=phone, email=email)
    if provider is None:
        provider = Provider(
            org_id=prop.org_id,
            name=_landlord_provider_name(arguments.get("name"), phone, email),
            trade=trade,
            contacts={
                "phone": phone,
                "email": email,
                "source": "landlord_supplied",
                "note": (arguments.get("note") or "").strip(),
            },
        )
        db = context.db
        db.add(provider)
        db.flush()
    else:
        contacts = {
            **(provider.contacts or {}),
            "source": "landlord_supplied",
            "note": (arguments.get("note") or "").strip(),
        }
        if phone:
            contacts["phone"] = phone
        if email:
            contacts["email"] = email
        provider.contacts = contacts
        if trade and provider.trade != trade:
            provider.trade = trade
        context.db.flush()

    append_action(
        context.property_id,
        context.db,
        "provider.register_contact",
        {
            "provider_id": str(provider.id),
            "provider_name": provider.name,
            "trade": provider.trade,
            "phone": _redact(phone),
            "email": _redact(email),
            "source": "landlord_supplied",
        },
    )
    return {
        "ok": True,
        "provider": model_to_dict(provider, ["id", "name", "trade", "contacts"]),
    }


def contact(context: ToolExecutionContext, arguments: dict) -> dict:
    provider = get_provider(context.property_id, context.db, UUID(arguments["provider_id"]))
    brief = arguments["brief"].strip()
    if not _landlord_approval_available(context):
        return {
            "ok": False,
            "refused": True,
            "error": "Landlord approval is required before contacting a repair provider.",
            "provider": model_to_dict(provider, ["id", "name", "trade", "contacts"]),
        }

    thread_id = f"provider-{provider.id}"
    message_result = _send_provider_message(provider, brief)
    sent = message_result.get("sent") is True
    if sent:
        append_message(
            context.property_id,
            context.db,
            ConversationParty.provider,
            thread_id,
            {
                "role": "agent",
                "body": brief,
                "channel": message_result["channel"],
                "provider_id": str(provider.id),
            },
        )
    append_action(
        context.property_id,
        context.db,
        "provider.contact",
        {
            "provider_id": str(provider.id),
            "provider_name": provider.name,
            "brief": brief,
            "thread_id": thread_id,
            "channel": message_result["channel"],
            "message_result": message_result,
        },
    )
    return {
        "ok": sent,
        "provider": model_to_dict(provider, ["id", "name", "trade", "contacts"]),
        "thread_opened": sent,
        "thread_id": thread_id,
        "message": message_result,
        "error": None if sent else message_result.get("error", "provider message was not sent"),
    }


def _property(context: ToolExecutionContext) -> Property | None:
    return context.db.execute(
        select(Property).where(Property.id == context.property_id)
    ).scalar_one_or_none()


def _property_address(context: ToolExecutionContext) -> str:
    prop = _property(context)
    return prop.address if prop else ""


def _provider_query(trade: str, area: str, property_address: str, constraints: str) -> str:
    parts = [
        f"{trade} repair service near {area}",
        "local contractor",
        "phone email emergency availability",
    ]
    if property_address and property_address != area:
        parts.append(f"property address {property_address}")
    if constraints:
        parts.append(constraints)
    return ". ".join(parts)


def _normalize_tavily_results(context: ToolExecutionContext, trade: str, result: dict) -> list[dict]:
    candidates = []
    for item in result.get("results", [])[:5]:
        title = item.get("title") or item.get("name") or "Unknown provider"
        url = item.get("url")
        content = item.get("content") or item.get("snippet") or ""
        contacts = _extract_contacts(content, url)
        provider = _upsert_external_provider(context, title, trade, contacts)
        candidates.append(
            {
                "provider_id": str(provider.id) if provider else None,
                "title": title,
                "url": url,
                "content": content,
                "score": item.get("score"),
                "contacts": contacts,
                "contactable": bool(contacts.get("phone") or contacts.get("email") or contacts.get("url")),
            }
        )
    return candidates


def _upsert_external_provider(
    context: ToolExecutionContext,
    name: str,
    trade: str,
    contacts: dict,
) -> Provider | None:
    prop = _property(context)
    if prop is None:
        return None
    normalized = " ".join(name.split())[:240] or "External provider"
    existing = context.db.execute(
        select(Provider).where(
            Provider.org_id == prop.org_id,
            Provider.name == normalized,
            Provider.trade == trade,
        )
    ).scalar_one_or_none()
    if existing:
        merged_contacts = {**existing.contacts, **contacts, "source": "tavily"}
        existing.contacts = merged_contacts
        context.db.flush()
        return existing

    provider = Provider(
        org_id=prop.org_id,
        name=normalized,
        trade=trade,
        contacts={**contacts, "source": "tavily"},
    )
    context.db.add(provider)
    context.db.flush()
    return provider


def _find_provider_by_contact(
    context: ToolExecutionContext,
    org_id,
    phone: str,
    email: str,
) -> Provider | None:
    providers = context.db.execute(select(Provider).where(Provider.org_id == org_id)).scalars().all()
    for provider in providers:
        contacts = provider.contacts or {}
        provider_phone = _normalize_phone(contacts.get("phone"))
        provider_email = str(contacts.get("email", "")).strip().lower()
        if phone and provider_phone == phone:
            return provider
        if email and provider_email == email:
            return provider
    return None


def _extract_contacts(content: str, url: str | None) -> dict:
    contacts: dict[str, str] = {}
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", content)
    phone = re.search(r"(?:\+33|0)\s?[1-9](?:[\s.-]?\d{2}){4}", content)
    if email:
        contacts["email"] = email.group(0)
    if phone:
        contacts["phone"] = _normalize_phone(phone.group(0))
    if url:
        contacts["url"] = url
    return contacts


def _normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    clean = value.strip().replace(" ", "").replace(".", "").replace("-", "").replace("(", "").replace(")", "")
    if clean.startswith("00"):
        clean = f"+{clean[2:]}"
    if clean.startswith("0") and len(clean) == 10:
        clean = f"+33{clean[1:]}"
    return clean


def _landlord_provider_name(name: str | None, phone: str, email: str) -> str:
    clean_name = " ".join((name or "").split())
    if clean_name:
        return clean_name[:240]
    contact = phone or email or "unknown contact"
    return f"Prestataire fourni par le proprietaire {contact}"[:240]


def _send_provider_message(provider: Provider, body: str) -> dict:
    contacts = provider.contacts or {}
    if contacts.get("email"):
        result = send_email("provider", body, [])
        return {
            **result,
            "to_provider": provider.name,
            "to_contact": _redact(contacts.get("email")),
            "channel": "email",
        }
    if contacts.get("phone"):
        result = send_whatsapp("provider", body, [], to_phone=contacts["phone"])
        return {
            **result,
            "to_provider": provider.name,
            "channel": "whatsapp",
        }
    if contacts.get("url"):
        return {
            "sent": True,
            "mode": "web_stub",
            "channel": "web",
            "to_role": "provider",
            "to_provider": provider.name,
            "to_contact": contacts["url"],
            "body": body,
            "attachments": [],
        }
    return {
        "sent": False,
        "mode": "missing_contact",
        "channel": "none",
        "to_role": "provider",
        "to_provider": provider.name,
        "error": "provider has no email, phone, or URL contact",
        "body": body,
        "attachments": [],
    }


def _landlord_approval_available(context: ToolExecutionContext) -> bool:
    if context.sender_role == "landlord":
        return True

    rows = (
        context.db.execute(
            select(ActionLog)
            .where(ActionLog.property_id == context.property_id)
            .order_by(ActionLog.created_at.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )
    for row in rows:
        payload = row.payload or {}
        if payload.get("approval") == "landlord_provider_coordination":
            return True
    return False


def _redact(value: str | None) -> str | None:
    if not value:
        return None
    if "@" in value:
        name, domain = value.split("@", 1)
        return f"{name[:2]}***@{domain}"
    return value[:3] + "***" + value[-2:] if len(value) > 5 else "***"
