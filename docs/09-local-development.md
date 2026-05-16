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

- Landlord: `hamza.landlord@example.com`
- Tenant: `amina.tenant@example.com`
- Tenant: `hugo.tenant@example.com`

For the hackathon demo, the local database can be enriched with additional
Hamza-owned tenants so the owner dashboard shows a realistic portfolio. Keep the
Amina/Hamza property clean before the final WhatsApp walkthrough if you want the
agent request flow to start from an empty context.

## Services

- Backend: http://localhost:8000
- Health: http://localhost:8000/health
- Frontend: http://localhost:5173
- Adminer: http://localhost:8082
- WhatsApp webhook: http://localhost:8000/webhooks/whatsapp
- Twilio WhatsApp webhook: http://localhost:8000/webhooks/twilio/whatsapp

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

## WhatsApp Voice Notes

When `WHATSAPP_MODE=twilio`, inbound WhatsApp text and voice notes use the same
webhook. Twilio sends voice media as `MediaUrl0` and `MediaContentType0`; the
backend downloads the file, sends `audio/ogg` voice notes to SLNG Unified STT as
Opus audio, and then passes the transcript to the agent as a normal current turn.

Useful log lines during manual testing:

```text
Twilio voice message transcribed
```

Required local variables for this flow:

```bash
WHATSAPP_MODE=twilio
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
SLNG_API_KEY=...
APP_AGENT_RUNTIME=llm
```

## Read Next

- [Prompt Engineering](06-prompt-engineering.md)
- [Tool Contracts](07-tool-contracts.md)
- [WhatsApp Cloud API Setup](11-whatsapp-cloud-setup.md)
- [Twilio WhatsApp Sandbox Setup](12-twilio-sandbox-setup.md)
