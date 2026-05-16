# Chris.AI Frontend

Vite + React + TypeScript portal for landlord and tenant operations.

The current app uses the FastAPI demo auth endpoints and role-scoped portal
dashboard endpoint. It shows:

- owner portfolio KPIs;
- properties and assigned tenants;
- tenant request progress;
- owner decision flags;
- plan steps, recent actions, and tool traces.

Demo accounts after `make seed`:

- Landlord: `marc.landlord@example.com`
- Tenant: `amina.tenant@example.com`
- Tenant: `hugo.tenant@example.com`

Run it through Docker Compose and open:

```text
http://localhost:5173
```
