# Security And Isolation

V1 focuses on property isolation, prompt injection defense, and document-fact
integrity.

## Property Isolation

Isolation is enforced at the data-loading boundary.

```mermaid
flowchart LR
    Request[Incoming request] --> Router[Resolve property_id]
    Router --> Guard[Isolation guard]
    Guard --> Repo[Scoped repository]
    Repo --> DB[(PostgreSQL)]
    DB --> Context[Single-property context]
    Context --> Agent[Chris]
```

The agent receives one property context only. It has no global memory and no
cross-property cache.

`render_system_prompt` rejects mixed property contexts. Repository helpers reject
missing `property_id`.

## Prompt Injection Defense

Message bodies are data, not instructions. Tenant, landlord, provider, email,
SLNG voice, web-search, and document text cannot change Chris behavior. Only the
supervisor channel can issue behavior-changing instructions, and those are still
bounded by isolation and legal-document rules.

## Document Facts

Document tools pull names, amounts, addresses, dates, lease terms, and payment
facts from relational tables. Free-text message content is never accepted as the
source of legal facts.

## In Scope For V1

- Cross-property context leakage.
- Receipt creation without landlord confirmation.
- Prompt injection inside user messages.
- Accidental human delegation of coordination tasks.
- Missing tool traceability.

## Out Of Scope For V1

- Full authentication and authorization.
- Row-level security policies.
- Production-grade WhatsApp, email, or voice delivery. The hackathon build has
  a Twilio Sandbox path for WhatsApp text/media and SLNG speech-to-text for
  inbound voice notes, but it is not production messaging infrastructure.
- E-signature and accounting exports.

## Read Next

- [Data Model](05-data-model.md)
- [Evaluation Strategy](08-evaluation-strategy.md)
