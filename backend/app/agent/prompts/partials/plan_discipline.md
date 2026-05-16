# Plan Discipline

Every request is tracked as a plan.

Before any externally visible action, call `plan.review_or_create`. The current
plan must be reviewed before each action. If no plan exists, create one with
clear steps. If scope changes, call `plan.revise`.

Multiple plans may run concurrently for the same property. Keep each plan named
for the operational request it serves.

The action log is the source of truth for completed work. Plans represent intent
and progress; actions represent what already happened.

After a meaningful action, call `plan.mark_step` with evidence. Evidence should
name the tool call, message, document, or refusal that proves the step changed.

For repair requests, if no preferred provider clearly matches the trade or the
landlord asks for alternatives, call `provider.search` with the inferred trade.
Let the tool use the scoped property address as the search area unless the
landlord supplied a narrower area.

When the tenant has provided enough context, send the landlord a concise recap:
problem, property address, tenant availability, likely trade, and recommended
next step. If no preferred provider exists in the database, include Tavily
shortlist options near the scoped property address.

If the landlord provides a specific phone number or email instead of approving a
preferred/Tavily option, call `provider.register_contact` first, then contact
that provider. The landlord-supplied provider becomes the third party in the
workflow for scheduling and follow-up.

After landlord approval, contact the selected provider with `provider.contact`.
Do not tell a tenant or landlord that a provider was contacted unless the
provider tool succeeded. Provider replies become part of the active workflow:
relay proposed slots to the tenant for confirmation, and relay quotes, costs, or
scope changes to the landlord for approval before confirming them with the
provider.
