# Document Rules

Documents are controlled outputs. They must use authoritative business data.

Receipts:

- A tenant saying "I paid" never triggers a receipt.
- Only a landlord-confirmed payment row can trigger a receipt.
- If confirmation is missing, ask the landlord for confirmation or escalate.

Legal facts:

- Names, amounts, addresses, dates, lease terms, and payment facts always come
  from relational tables through document tools.
- Never copy legal facts from chat text into a document.
- The documents tool must refuse document creation when facts are supplied as
  free text.

Quote summaries:

- Summarize received quotes for landlord review.
- Present options to the landlord, not the tenant.

Intervention reports:

- Pull facts from the provider/job record.
- Use message content only as non-authoritative notes when explicitly labeled.

Lease documents:

- Use relational lease, party, and property data only.
- Escalate if required legal data is missing.
