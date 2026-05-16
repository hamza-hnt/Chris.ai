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
