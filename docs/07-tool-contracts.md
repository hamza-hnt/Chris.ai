# Tool Contracts

Tool schemas live in `backend/app/agent/tools/schemas.py`. Providers receive the
same schema list regardless of model vendor.

The LLM never supplies `property_id`. The tool executor receives it from the
trusted execution context.

## Tools

`plan.review_or_create(plan_name, steps[])`: required before externally visible
actions. Creates or reviews the active plan.

`plan.mark_step(plan_id, step_index, status, evidence?)`: records progress after
meaningful work.

`plan.revise(plan_id, new_steps[])`: replaces steps when the request scope
changes.

`messaging.send(to_role, channel, body, attachments?)`: sends through stubbed
WhatsApp, email, or SLNG voice integrations.

`messaging.ask_question(to_role, body)`: asks exactly one question. The tool
refuses bodies with zero or multiple question marks.

`provider.list_preferred(trade)`: lists preferred providers for the property.

`provider.search(trade, area, constraints)`: runs Tavily-backed outside search.

`provider.contact(provider_id, brief)`: opens a scoped provider thread.

`documents.create_receipt(payment_id)`: refuses unless the payment belongs to
the property and has landlord confirmation.

`documents.create_intervention_report(job_id)`: creates a stubbed report record
from authoritative job data once the job table exists.

`documents.create_quote_summary(job_id)`: creates a stubbed quote summary for
landlord review.

`web_search(query)`: runs Tavily search.

`escalate(reason, severity)`: records supervisor attention flags.

## Traceability

Every tool call is written to `tool_traces` with `property_id`, `turn_id`, input,
output, duration, and timestamp.

## Read Next

- [Single Agent](03-single-agent.md)
- [Data Model](05-data-model.md)
