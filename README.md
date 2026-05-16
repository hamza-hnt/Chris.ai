# Chris.AI

Chris.AI is an autonomous AI property management platform. It coordinates tenants,
landlords, providers, and supervisors through a stateless FastAPI backend, a
context-injected Chris agent, PostgreSQL relational tables, and JSONB-backed
agent memory.

This repository is the first build scaffold. The main deliverable is the prompt
and evaluation layer for a single property-scoped Chris instance. The rest of the
system is intentionally thin but runnable.

## Run In 60 Seconds

1. Create a local environment file:

   ```bash
   cp .env.example .env
   ```

2. Fill in placeholder secret values in `.env`.

3. Start the stack:

   ```bash
   make up
   ```

4. Apply migrations and seed the demo portfolio:

   ```bash
   make migrate
   make seed
   ```

5. Run the prompt evaluation suite:

   ```bash
   make eval
   ```

Services:

- Backend API: http://localhost:8000
- API health: http://localhost:8000/health
- Frontend dashboard: http://localhost:5173
- Adminer: http://localhost:8082

Demo login accounts:

- Landlord: `marc.landlord@example.com`
- Tenant: `amina.tenant@example.com`
- Tenant: `hugo.tenant@example.com`

## What Is Implemented

- Docker Compose stack for PostgreSQL, FastAPI, Vite, and Adminer.
- Demo login and role-scoped dashboard access. Landlords see all tenant
  requests for their properties; tenants see only their own request progress.
- Pydantic settings with fail-fast secret validation.
- Alembic migration for the relational and JSONB-backed data model.
- Context-injected Chris agent with provider abstraction and stubbed tools.
- Composable system prompt partials under `backend/app/agent/prompts/`.
- Prompt evaluation harness with five mandatory scenario families.
- Deterministic orchestration modules for routing, alerts, intervention, and
  isolation.

## Where To Read Next

- [Overview](docs/01-overview.md)
- [Architecture](docs/02-architecture.md)
- [Single Agent](docs/03-single-agent.md)
- [Prompt Engineering](docs/06-prompt-engineering.md)
- [Evaluation Strategy](docs/08-evaluation-strategy.md)
- [Local Development](docs/09-local-development.md)
- [WhatsApp Cloud API Setup](docs/11-whatsapp-cloud-setup.md)
