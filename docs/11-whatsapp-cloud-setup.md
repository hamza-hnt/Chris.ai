# WhatsApp Cloud API Setup

This guide connects the local Chris.AI backend to Meta WhatsApp Cloud API for
development testing.

## Security

Never commit WhatsApp credentials. Keep them only in `.env`.

If an access token was pasted into chat, issue tracker, logs, or any shared
surface, rotate it in Meta before using it for production. Prefer a system user
access token over a temporary token for longer-running environments.

## Environment

Add these values to `.env`:

```bash
WHATSAPP_MODE=cloud
WHATSAPP_GRAPH_API_VERSION=v25.0
WHATSAPP_ACCESS_TOKEN=<meta-access-token>
WHATSAPP_BUSINESS_ACCOUNT_ID=<whatsapp-business-account-id>
WHATSAPP_PHONE_NUMBER_ID=<phone-number-id>
WHATSAPP_VERIFY_TOKEN=<long-random-string-you-choose>
WHATSAPP_APP_SECRET=<meta-app-secret>
```

`WHATSAPP_VERIFY_TOKEN` is not provided by Meta. Choose a long random string,
store it in `.env`, and paste the same value into the Meta webhook configuration.

`WHATSAPP_APP_SECRET` is used to validate the `X-Hub-Signature-256` header on
incoming webhooks. It is optional in development but required in production.

## Local Tunnel

Meta requires a public HTTPS callback URL. For local development:

```bash
make up
ngrok http 8000
```

Use the HTTPS URL from ngrok:

```text
https://<ngrok-subdomain>.ngrok-free.app/webhooks/whatsapp
```

## Meta Configuration

In the Meta app dashboard:

1. Open WhatsApp > Configuration.
2. Set Callback URL to the public HTTPS URL ending in `/webhooks/whatsapp`.
3. Set Verify token to the exact value of `WHATSAPP_VERIFY_TOKEN`.
4. Verify and save.
5. Subscribe the app to the `messages` webhook field.

The backend responds to Meta's verification challenge on `GET /webhooks/whatsapp`.
Incoming messages are received on `POST /webhooks/whatsapp`.

## Seeded Contacts

The router resolves an incoming WhatsApp sender by matching the sender phone
number against `users.phone`.

After `make seed`, demo users use fake French phone numbers. To test from your
own WhatsApp phone, update the tenant or landlord phone in PostgreSQL to match
your real WhatsApp number in E.164 format:

```sql
update users
set phone = '+33612345678'
where email = 'amina.tenant@example.com';
```

Use Adminer at `http://localhost:8082` or run the SQL directly in Postgres.

## Smoke Tests

Verify the challenge endpoint locally:

```bash
curl "http://localhost:8000/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=$WHATSAPP_VERIFY_TOKEN&hub.challenge=ok"
```

Expected response:

```text
ok
```

Send a local Meta-shaped webhook without signature validation:

```bash
curl -X POST http://localhost:8000/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "field": "messages",
        "value": {
          "messages": [{
            "id": "wamid.local-test",
            "from": "33600000001",
            "type": "text",
            "text": {"body": "There is a leak under the sink"}
          }]
        }
      }]
    }]
  }'
```

Expected response includes `processed: 1` if the sender phone matches a seeded
user.

## Current Limits

- Text messages are parsed.
- Non-text WhatsApp messages are acknowledged but ignored.
- Webhook processing is synchronous for v1.
- Outbound WhatsApp sends work for tenant and landlord roles when their phone
  number is present in the scoped lease.
