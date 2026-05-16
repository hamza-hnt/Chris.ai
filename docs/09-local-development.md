# Local Development

## Requirements

- Docker and Docker Compose
- Make
- A local `.env` file based on `.env.example`

## Setup

```bash
cp .env.example .env
make check-env
make up
```

In another terminal:

```bash
make migrate
make seed
make sample
make eval
```

`make seed` rebuilds the demo portfolio with one landlord and two tenants:

- Landlord: `marc.landlord@example.com`
- Tenant: `amina.tenant@example.com`
- Tenant: `hugo.tenant@example.com`

## Services

- Backend: http://localhost:8000
- Health: http://localhost:8000/health
- Frontend: http://localhost:5173
- Adminer: http://localhost:8082

Adminer defaults:

- System: PostgreSQL
- Server: postgres
- Username: value of `POSTGRES_USER`
- Password: value of `POSTGRES_PASSWORD`
- Database: value of `POSTGRES_DB`

## Common Workflow

1. Edit prompt partials or tool contracts.
2. Run `make eval`.
3. If backend code changed, run `make up` and inspect `/health`.
4. Run `make seed` and open the frontend portal to test role-scoped dashboards.
5. Run `make sample` to produce tool traces.

## Read Next

- [Prompt Engineering](06-prompt-engineering.md)
- [Tool Contracts](07-tool-contracts.md)
